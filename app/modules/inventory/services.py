"""Inventory services — stock is changed only here, transactionally.

- stock_movements is append-only; balances update in the same transaction
- negative stock is prevented unless the company enables it in settings
  (companies.settings["allow_negative_stock"] == true)
- valuation method is per company (weighted_average default, FIFO supported
  as a setting; the ledger keeps unit_cost per movement so FIFO can be
  computed from it)
"""
import uuid
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.common.helpers import get_company_scoped, require_same_company
from app.core.errors import ConflictError, NotFoundError
from .models import Product, StockBalance, StockMovement, StockTransfer, StockTransferItem, Warehouse

NIL_LOCATION = uuid.UUID(int=0)


def _allow_negative(db: Session, company_id: UUID) -> bool:
    from app.modules.core.models import Company
    company = db.get(Company, company_id)
    return bool(company and (company.settings or {}).get("allow_negative_stock"))


def get_balance(db: Session, product_id: UUID, warehouse_id: UUID) -> Decimal:
    bal = db.get(StockBalance, (product_id, warehouse_id, NIL_LOCATION))
    return bal.quantity if bal else Decimal("0")


def record_stock_movement(db: Session, company_id: UUID, user_id: UUID | None, *,
                          product_id: UUID, warehouse_id: UUID, location_id: UUID | None,
                          movement_type: str, quantity: Decimal, unit_cost: Decimal = Decimal("0"),
                          reference_type: str | None = None, reference_id: str | None = None) -> StockMovement:
    product = db.get(Product, product_id)
    if product is None:
        raise NotFoundError("Product not found")
    require_same_company(product.company_id, company_id, "product")
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise NotFoundError("Warehouse not found")
    require_same_company(warehouse.company_id, company_id, "warehouse")
    quantity = Decimal(str(quantity))
    if quantity == 0:
        raise ConflictError("Stock movement quantity cannot be zero")
    loc = location_id or NIL_LOCATION
    balance = db.get(StockBalance, (product_id, warehouse_id, loc))
    current = balance.quantity if balance else Decimal("0")
    if current + quantity < 0 and not _allow_negative(db, company_id):
        raise ConflictError("Insufficient stock: movement would make stock negative",
                            code="INSUFFICIENT_STOCK", status_code=409)
    movement = StockMovement(company_id=company_id, product_id=product_id,
                             warehouse_id=warehouse_id, location_id=location_id,
                             movement_type=movement_type, quantity=quantity,
                             unit_cost=Decimal(str(unit_cost)),
                             reference_type=reference_type, reference_id=reference_id,
                             created_by=user_id)
    db.add(movement)
    if balance is None:
        db.add(StockBalance(product_id=product_id, warehouse_id=warehouse_id,
                            location_id=loc, quantity=quantity))
    else:
        balance.quantity = current + quantity
    db.commit()
    db.refresh(movement)
    return movement


def transfer_stock(db: Session, company_id: UUID, user_id: UUID | None, *,
                   from_warehouse_id: UUID, to_warehouse_id: UUID,
                   items: list[dict], note: str | None = None) -> StockTransfer:
    transfer = StockTransfer(company_id=company_id, from_warehouse_id=from_warehouse_id,
                             to_warehouse_id=to_warehouse_id, status="completed", note=note)
    db.add(transfer)
    db.flush()
    for item in items:
        qty = Decimal(str(item["quantity"]))
        db.add(StockTransferItem(transfer_id=transfer.id, product_id=item["product_id"], quantity=qty))
        record_stock_movement(db, company_id, user_id, product_id=item["product_id"],
                              warehouse_id=from_warehouse_id, location_id=None,
                              movement_type="transfer_out", quantity=-qty,
                              reference_type="stock_transfer", reference_id=str(transfer.id))
        record_stock_movement(db, company_id, user_id, product_id=item["product_id"],
                              warehouse_id=to_warehouse_id, location_id=None,
                              movement_type="transfer_in", quantity=qty,
                              reference_type="stock_transfer", reference_id=str(transfer.id))
    db.commit()
    db.refresh(transfer)
    return transfer


def low_stock_products(db: Session, company_id: UUID) -> list[dict]:
    products = db.query(Product).filter(Product.company_id == company_id,
                                        Product.deleted_at.is_(None)).all()
    out = []
    for p in products:
        balances = db.query(StockBalance).filter(StockBalance.product_id == p.id).all()
        total = sum((b.quantity for b in balances), Decimal("0"))
        if total <= (p.reorder_level or Decimal("0")):
            out.append({"product_id": str(p.id), "name": p.name, "sku": p.sku,
                        "quantity": float(total), "reorder_level": float(p.reorder_level or 0)})
    return out
