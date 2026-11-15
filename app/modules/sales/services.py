"""Sales services.

- A quotation is NOT a sale: approving/creating one creates no revenue,
  no stock movement and no journal.
- A sales order is NOT automatic revenue recognition: revenue is only
  recognised when an invoice is posted (finance.post_invoice).
- Fulfilment issues stock through the inventory service, transactionally.
"""
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.common.helpers import get_company_scoped, next_code
from app.core.errors import ConflictError
from .models import Customer, Quotation, QuotationItem, SalesOrder, SalesOrderItem


def _total(items: list[dict]) -> Decimal:
    return sum(Decimal(str(i.get("quantity", 0))) * Decimal(str(i.get("unit_price", 0))) for i in items)


def create_quotation(db: Session, company_id: UUID, customer_id: UUID, currency: str, items: list[dict]) -> Quotation:
    customer = db.get(Customer, customer_id)
    if customer is None or customer.company_id != company_id:
        raise ConflictError("Customer not found")
    q = Quotation(company_id=company_id, customer_id=customer_id,
                  code=next_code(db, Quotation, company_id, "QT"),
                  currency=currency, total=_total(items))
    db.add(q)
    db.flush()
    for i in items:
        db.add(QuotationItem(quotation_id=q.id, product_id=i["product_id"],
                             quantity=Decimal(str(i["quantity"])), unit_price=Decimal(str(i["unit_price"]))))
    db.commit()
    db.refresh(q)
    return q


def approve_quotation(db: Session, company_id: UUID, quotation_id: UUID) -> Quotation:
    q = get_company_scoped(db, Quotation, quotation_id, company_id)
    if q.status not in ("draft", "pending_approval"):
        raise ConflictError("Quotation cannot be approved in its current status")
    q.status = "approved"
    db.commit()
    db.refresh(q)
    return q


def convert_to_order(db: Session, company_id: UUID, quotation_id: UUID) -> SalesOrder:
    q = get_company_scoped(db, Quotation, quotation_id, company_id)
    if q.status != "approved":
        raise ConflictError("Only an approved quotation can be converted to a sales order")
    items = db.query(QuotationItem).filter(QuotationItem.quotation_id == q.id).all()
    order = SalesOrder(company_id=company_id, customer_id=q.customer_id, quotation_id=q.id,
                       code=next_code(db, SalesOrder, company_id, "SO"),
                       currency=q.currency, total=q.total, status="confirmed")
    db.add(order)
    db.flush()
    for i in items:
        db.add(SalesOrderItem(order_id=order.id, product_id=i.product_id,
                              quantity=i.quantity, unit_price=i.unit_price))
    q.status = "converted"
    db.commit()
    db.refresh(order)
    return order


def fulfil_order(db: Session, company_id: UUID, user_id: UUID, order_id: UUID, warehouse_id: UUID) -> SalesOrder:
    """Issue stock for the order. No revenue is recognised here."""
    from app.modules.inventory.services import record_stock_movement
    order = get_company_scoped(db, SalesOrder, order_id, company_id)
    if order.status not in ("confirmed", "draft"):
        raise ConflictError("Sales order cannot be fulfilled in its current status")
    items = db.query(SalesOrderItem).filter(SalesOrderItem.order_id == order.id).all()
    for item in items:
        remaining = item.quantity - (item.fulfilled_quantity or Decimal("0"))
        if remaining <= 0:
            continue
        record_stock_movement(db, company_id, user_id, product_id=item.product_id,
                              warehouse_id=warehouse_id, location_id=None,
                              movement_type="issue", quantity=-remaining,
                              reference_type="sales_order", reference_id=str(order.id))
        item.fulfilled_quantity = item.quantity
    order.status = "fulfilled"
    db.commit()
    db.refresh(order)
    return order
