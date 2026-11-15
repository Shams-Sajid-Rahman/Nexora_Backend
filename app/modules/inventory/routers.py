"""Inventory routers."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.crud import make_crud_router
from app.common.pagination import ok_list
from app.common.serializers import serialize, serialize_list
from app.core.deps import get_current_company, get_current_user, require_permission
from app.db.session import get_db
from . import services
from .models import (Product, ProductCategory, StockMovement, UnitOfMeasure,
                     Warehouse, WarehouseLocation)
from .schemas import StockMovementCreate, StockTransferCreate

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


@router.post("/stock-movements", status_code=201, dependencies=[Depends(require_permission("inventory.stock.adjust"))])
def create_movement(payload: StockMovementCreate, db: Session = Depends(get_db),
                    user=Depends(get_current_user), company=Depends(get_current_company)):
    m = services.record_stock_movement(db, company.id, user.id, product_id=payload.product_id,
                                       warehouse_id=payload.warehouse_id, location_id=payload.location_id,
                                       movement_type=payload.movement_type, quantity=payload.quantity,
                                       unit_cost=payload.unit_cost, reference_type=payload.reference_type,
                                       reference_id=payload.reference_id)
    return {"data": serialize(m), "meta": None}


@router.get("/stock-movements", dependencies=[Depends(require_permission("inventory.stock.view"))])
def list_movements(db: Session = Depends(get_db), company=Depends(get_current_company),
                   page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                   product_id: UUID | None = None):
    q = db.query(StockMovement).filter(StockMovement.company_id == company.id).order_by(StockMovement.created_at.desc())
    if product_id:
        q = q.filter(StockMovement.product_id == product_id)
    total = q.count()
    return ok_list(serialize_list(q.offset((page - 1) * page_size).limit(page_size).all()), total, page, page_size)


@router.get("/stock-balances", dependencies=[Depends(require_permission("inventory.stock.view"))])
def list_balances(db: Session = Depends(get_db), company=Depends(get_current_company)):
    from .models import StockBalance
    balances = db.query(StockBalance).all()
    # balances are company-scoped via their product
    out = []
    for b in balances:
        product = db.get(Product, b.product_id)
        if product and product.company_id == company.id:
            out.append({"product_id": str(b.product_id), "warehouse_id": str(b.warehouse_id),
                        "quantity": float(b.quantity)})
    return {"data": out, "meta": None}


@router.post("/stock-transfers", status_code=201, dependencies=[Depends(require_permission("inventory.stock.adjust"))])
def create_transfer(payload: StockTransferCreate, db: Session = Depends(get_db),
                    user=Depends(get_current_user), company=Depends(get_current_company)):
    t = services.transfer_stock(db, company.id, user.id, from_warehouse_id=payload.from_warehouse_id,
                                to_warehouse_id=payload.to_warehouse_id, items=payload.items, note=payload.note)
    return {"data": serialize(t), "meta": None}


@router.get("/low-stock", dependencies=[Depends(require_permission("inventory.stock.view"))])
def low_stock(db: Session = Depends(get_db), company=Depends(get_current_company)):
    return {"data": services.low_stock_products(db, company.id), "meta": None}


product_router = make_crud_router(Product, prefix="/api/v1/inventory/products", permission="inventory.product", name="Product", code_prefix="PRD")
category_router = make_crud_router(ProductCategory, prefix="/api/v1/inventory/categories", permission="inventory.product", name="ProductCategory")
warehouse_router = make_crud_router(Warehouse, prefix="/api/v1/inventory/warehouses", permission="inventory.product", name="Warehouse", code_prefix="WH")
uom_router = make_crud_router(UnitOfMeasure, prefix="/api/v1/inventory/units", permission="inventory.product", name="UnitOfMeasure")

routers = [router, product_router, category_router, warehouse_router, uom_router]
