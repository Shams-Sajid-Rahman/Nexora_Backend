"""Company-scoping helpers (docs/05 §5.4). Every single-record read must
check record.company_id == active company, and return 404 (not 403) when
the record belongs to another company, so its existence is not leaked."""
from typing import TypeVar
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError

T = TypeVar("T")


def get_company_scoped(db: Session, model, record_id: UUID, company_id: UUID):
    """Load by id; 404 if missing OR owned by another company."""
    obj = db.get(model, record_id)
    if obj is None:
        raise NotFoundError(f"{model.__name__} not found")
    owner = getattr(obj, "company_id", None)
    if owner is not None and owner != company_id:
        raise NotFoundError(f"{model.__name__} not found")
    return obj


def require_same_company(obj_company_id: UUID | None, company_id: UUID, what: str = "record"):
    if obj_company_id is not None and obj_company_id != company_id:
        raise NotFoundError(f"{what} not found")


def next_code(db: Session, model, company_id: UUID, prefix: str, code_field: str = "code") -> str:
    """Company-specific sequential code, e.g. INV-2026-0001."""
    from datetime import datetime
    year = datetime.now().year
    count = db.query(model).filter(
        getattr(model, "company_id") == company_id).count()
    return f"{prefix}-{year}-{count + 1:04d}"


def to_aware(dt):
    """SQLite returns naive datetimes for timezone-aware columns; Postgres
    returns aware ones. Normalise to aware UTC for safe comparisons."""
    from datetime import timezone
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
