"""Purchase schemas."""
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class PurchaseOrderCreate(BaseModel):
    supplier_id: UUID
    currency: str = "BDT"
    items: list[dict] = []  # [{product_id, quantity, unit_price}]


class GoodsReceiptCreate(BaseModel):
    order_id: UUID
    warehouse_id: UUID
    items: list[dict] = []  # [{order_item_id, quantity}]
