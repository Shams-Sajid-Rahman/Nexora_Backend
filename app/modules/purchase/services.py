"""Purchase services. Goods receipts update stock ONLY through the
inventory service, and partial deliveries are tracked per order line."""
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.common.helpers import get_company_scoped, next_code
from app.core.errors import ConflictError
from .models import (GoodsReceipt, GoodsReceiptItem, PurchaseOrder,
                     PurchaseOrderItem, Supplier)


def create_order(db: Session, company_id: UUID, supplier_id: UUID, currency: str, items: list[dict]) -> PurchaseOrder:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None or supplier.company_id != company_id:
        raise ConflictError("Supplier not found")
    total = sum(Decimal(str(i.get("quantity", 0))) * Decimal(str(i.get("unit_price", 0))) for i in items)
    order = PurchaseOrder(company_id=company_id, supplier_id=supplier_id,
                          code=next_code(db, PurchaseOrder, company_id, "PO"),
                          currency=currency, total=total, status="draft")
    db.add(order)
    db.flush()
    for i in items:
        db.add(PurchaseOrderItem(order_id=order.id, product_id=i["product_id"],
                                 quantity=Decimal(str(i["quantity"])),
                                 unit_price=Decimal(str(i["unit_price"]))))
    db.commit()
    db.refresh(order)
    return order


def receive_goods(db: Session, company_id: UUID, user_id: UUID, *,
                  order_id: UUID, warehouse_id: UUID, items: list[dict]) -> GoodsReceipt:
    from app.modules.inventory.services import record_stock_movement
    order = get_company_scoped(db, PurchaseOrder, order_id, company_id)
    receipt = GoodsReceipt(order_id=order.id, warehouse_id=warehouse_id, received_by=user_id)
    db.add(receipt)
    db.flush()
    for item in items:
        line = db.get(PurchaseOrderItem, item["order_item_id"])
        if line is None or line.order_id != order.id:
            raise ConflictError("Purchase order item not found")
        qty = Decimal(str(item["quantity"]))
        if line.received_quantity + qty > line.quantity:
            raise ConflictError("Received quantity exceeds ordered quantity")
        db.add(GoodsReceiptItem(receipt_id=receipt.id, order_item_id=line.id, quantity=qty))
        line.received_quantity = line.received_quantity + qty
        record_stock_movement(db, company_id, user_id, product_id=line.product_id,
                              warehouse_id=warehouse_id, location_id=None,
                              movement_type="receipt", quantity=qty, unit_cost=line.unit_price,
                              reference_type="goods_receipt", reference_id=str(receipt.id))
    lines = db.query(PurchaseOrderItem).filter(PurchaseOrderItem.order_id == order.id).all()
    order.status = "received" if all(l.received_quantity >= l.quantity for l in lines) else "partially_received"
    db.commit()
    db.refresh(receipt)
    return receipt
