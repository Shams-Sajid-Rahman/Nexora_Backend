"""Sales routers."""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.crud import make_crud_router
from app.common.serializers import serialize
from app.core.deps import get_current_company, get_current_user, require_permission
from app.db.session import get_db
from . import services
from .models import Customer, Lead, Opportunity, Quotation, SalesOrder
from .schemas import CustomerCreate, QuotationCreate, SalesOrderCreate

router = APIRouter(prefix="/api/v1/sales", tags=["sales"])


@router.post("/customers", status_code=201, dependencies=[Depends(require_permission("sales.customer.create"))])
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db), company=Depends(get_current_company)):
    c = Customer(company_id=company.id, **payload.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"data": serialize(c), "meta": None}


@router.post("/quotations", status_code=201, dependencies=[Depends(require_permission("sales.quotation.create"))])
def create_quotation(payload: QuotationCreate, db: Session = Depends(get_db), company=Depends(get_current_company)):
    q = services.create_quotation(db, company.id, payload.customer_id, payload.currency, payload.items)
    return {"data": serialize(q), "meta": None}


@router.post("/quotations/{quotation_id}/approve", dependencies=[Depends(require_permission("sales.quotation.approve"))])
def approve_quotation(quotation_id: UUID, db: Session = Depends(get_db), company=Depends(get_current_company)):
    q = services.approve_quotation(db, company.id, quotation_id)
    return {"data": serialize(q), "meta": None}


@router.post("/quotations/{quotation_id}/convert", dependencies=[Depends(require_permission("sales.order.create"))])
def convert(quotation_id: UUID, db: Session = Depends(get_db), company=Depends(get_current_company)):
    order = services.convert_to_order(db, company.id, quotation_id)
    return {"data": serialize(order), "meta": None}


@router.post("/orders/{order_id}/fulfil", dependencies=[Depends(require_permission("sales.order.fulfil"))])
def fulfil(order_id: UUID, warehouse_id: UUID, db: Session = Depends(get_db),
           user=Depends(get_current_user), company=Depends(get_current_company)):
    order = services.fulfil_order(db, company.id, user.id, order_id, warehouse_id)
    return {"data": serialize(order), "meta": None}


customer_router = make_crud_router(Customer, prefix="/api/v1/sales/customers-list", permission="sales.customer", name="Customer", code_prefix="CUST")
quotation_router = make_crud_router(Quotation, prefix="/api/v1/sales/quotations-list", permission="sales.quotation", name="Quotation")
order_router = make_crud_router(SalesOrder, prefix="/api/v1/sales/orders-list", permission="sales.order", name="SalesOrder")
lead_router = make_crud_router(Lead, prefix="/api/v1/sales/leads", permission="sales.customer", name="Lead")
opportunity_router = make_crud_router(Opportunity, prefix="/api/v1/sales/opportunities", permission="sales.customer", name="Opportunity")

routers = [router, customer_router, quotation_router, order_router, lead_router, opportunity_router]
