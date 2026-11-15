"""Purchase routers."""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.crud import make_crud_router
from app.common.serializers import serialize
from app.core.deps import get_current_company, get_current_user, require_permission
from app.db.session import get_db
from . import services
from .models import PurchaseOrder, PurchaseRequest, Supplier
from .schemas import GoodsReceiptCreate, PurchaseOrderCreate

router = APIRouter(prefix="/api/v1/purchases", tags=["purchases"])


@router.post("/orders", status_code=201, dependencies=[Depends(require_permission("purchase.order.create"))])
def create_order(payload: PurchaseOrderCreate, db: Session = Depends(get_db), company=Depends(get_current_company)):
    order = services.create_order(db, company.id, payload.supplier_id, payload.currency, payload.items)
    return {"data": serialize(order), "meta": None}


@router.post("/orders/{order_id}/approve", dependencies=[Depends(require_permission("purchase.order.approve"))])
def approve_order(order_id: UUID, db: Session = Depends(get_db), company=Depends(get_current_company)):
    from app.common.helpers import get_company_scoped
    order = get_company_scoped(db, PurchaseOrder, order_id, company.id)
    order.status = "approved"
    db.commit()
    db.refresh(order)
    return {"data": serialize(order), "meta": None}


@router.post("/goods-receipts", status_code=201, dependencies=[Depends(require_permission("purchase.receipt.create"))])
def receive(payload: GoodsReceiptCreate, db: Session = Depends(get_db),
            user=Depends(get_current_user), company=Depends(get_current_company)):
    receipt = services.receive_goods(db, company.id, user.id, order_id=payload.order_id,
                                     warehouse_id=payload.warehouse_id, items=payload.items)
    return {"data": serialize(receipt), "meta": None}


supplier_router = make_crud_router(Supplier, prefix="/api/v1/purchases/suppliers", permission="purchase.supplier", name="Supplier", code_prefix="SUP")
request_router = make_crud_router(PurchaseRequest, prefix="/api/v1/purchases/requests", permission="purchase.order", name="PurchaseRequest", code_prefix="PR")
order_router = make_crud_router(PurchaseOrder, prefix="/api/v1/purchases/orders-list", permission="purchase.order", name="PurchaseOrder")

routers = [router, supplier_router, request_router, order_router]
