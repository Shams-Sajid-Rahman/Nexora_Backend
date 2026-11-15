"""Generic company-scoped CRUD used by routers.

Business invariants live in each module's services.py — this layer only
does scoping, pagination and the standard envelope. Sensitive flows
(journals, stock, payroll) do NOT use the generic create/update paths;
they go through their module services.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, create_model
from sqlalchemy import Boolean, Date, DateTime, Integer, JSON, Numeric, String, Uuid
from sqlalchemy.orm import Session

from app.common.helpers import get_company_scoped, next_code
from app.common.pagination import ok_list
from app.common.serializers import serialize, serialize_list
from app.core.deps import get_current_company, get_current_user, require_permission
from app.core.errors import NotFoundError
from app.db.session import get_db


def schema_for_model(model, name: str):
    """Build a Pydantic create-schema from SQLAlchemy columns.

    Required = non-nullable columns with no server/client default, excluding
    id / company_id / created_at / updated_at / deleted_at.
    """
    skip = {"id", "company_id", "created_at", "updated_at", "deleted_at"}
    fields: dict[str, Any] = {}
    for col in model.__table__.columns:
        if col.name in skip:
            continue
        py = str
        if isinstance(col.type, Boolean):
            py = bool
        elif isinstance(col.type, Integer):
            py = int
        elif isinstance(col.type, Numeric):
            py = Decimal
        elif isinstance(col.type, DateTime):
            py = datetime
        elif isinstance(col.type, Date):
            py = date
        elif isinstance(col.type, Uuid):
            py = UUID
        elif isinstance(col.type, JSON):
            py = dict | None  # type: ignore
        required = (not col.nullable and col.default is None and col.server_default is None)
        fields[col.name] = (py, ... if required else None)
    return create_model(name, **fields)


def make_crud_router(model, *, prefix: str, permission: str, name: str,
                     code_prefix: str | None = None, search_field: str = "name"):
    """Return an APIRouter with list/create/get/patch/delete for `model`."""
    router = APIRouter(prefix=prefix, tags=[name])
    CreateSchema = schema_for_model(model, f"{name}Create")
    UpdateSchema = schema_for_model(model, f"{name}Update")
    # updates are all-optional
    UpdateSchema = create_model(
        f"{name}Update", **{k: (v.annotation, None) for k, v in UpdateSchema.model_fields.items()})

    @router.get("/", dependencies=[Depends(require_permission(f"{permission}.view"))])
    def list_items(db: Session = Depends(get_db), company=Depends(get_current_company),
                   page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                   status: str | None = None, search: str | None = None):
        q = db.query(model)
        if hasattr(model, "company_id"):
            q = q.filter(model.company_id == company.id)
        if hasattr(model, "deleted_at"):
            q = q.filter(model.deleted_at.is_(None))
        if status and hasattr(model, "status"):
            q = q.filter(model.status == status)
        if search and hasattr(model, search_field):
            q = q.filter(getattr(model, search_field).ilike(f"%{search}%"))
        total = q.count()
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return ok_list(serialize_list(items), total, page, page_size)

    @router.post("/", status_code=201, dependencies=[Depends(require_permission(f"{permission}.create"))])
    def create_item(payload: CreateSchema, db: Session = Depends(get_db),
                    user=Depends(get_current_user), company=Depends(get_current_company)):
        data = payload.model_dump(exclude_unset=True)
        if hasattr(model, "company_id"):
            data["company_id"] = company.id
        if code_prefix and hasattr(model, "code") and not data.get("code"):
            data["code"] = next_code(db, model, company.id, code_prefix)
        obj = model(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return {"data": serialize(obj), "meta": None}

    @router.get("/{item_id}", dependencies=[Depends(require_permission(f"{permission}.view"))])
    def get_item(item_id: UUID, db: Session = Depends(get_db),
                 company=Depends(get_current_company)):
        if hasattr(model, "company_id"):
            obj = get_company_scoped(db, model, item_id, company.id)
        else:
            obj = db.get(model, item_id)
            if obj is None:
                raise NotFoundError(f"{name} not found")
        return {"data": serialize(obj), "meta": None}

    @router.patch("/{item_id}", dependencies=[Depends(require_permission(f"{permission}.update"))])
    def update_item(item_id: UUID, payload: UpdateSchema, db: Session = Depends(get_db),
                    company=Depends(get_current_company)):
        if hasattr(model, "company_id"):
            obj = get_company_scoped(db, model, item_id, company.id)
        else:
            obj = db.get(model, item_id)
            if obj is None:
                raise NotFoundError(f"{name} not found")
        for k, v in payload.model_dump(exclude_unset=True).items():
            if k in ("company_id", "id"):
                continue
            setattr(obj, k, v)
        db.commit()
        db.refresh(obj)
        return {"data": serialize(obj), "meta": None}

    @router.delete("/{item_id}", dependencies=[Depends(require_permission(f"{permission}.delete"))])
    def delete_item(item_id: UUID, db: Session = Depends(get_db),
                    company=Depends(get_current_company)):
        if hasattr(model, "company_id"):
            obj = get_company_scoped(db, model, item_id, company.id)
        else:
            obj = db.get(model, item_id)
            if obj is None:
                raise NotFoundError(f"{name} not found")
        if hasattr(obj, "deleted_at"):
            from datetime import datetime, timezone
            obj.deleted_at = datetime.now(timezone.utc)
        else:
            db.delete(obj)
        db.commit()
        return {"data": {"deleted": True, "id": str(item_id)}, "meta": None}

    return router
