"""Inventory schemas."""
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class StockMovementCreate(BaseModel):
    product_id: UUID
    warehouse_id: UUID
    location_id: UUID | None = None
    movement_type: str  # receipt|issue|transfer_in|transfer_out|adjustment
    quantity: Decimal  # signed: positive in, negative out
    unit_cost: Decimal = Decimal("0")
    reference_type: str | None = None
    reference_id: str | None = None


class StockTransferCreate(BaseModel):
    from_warehouse_id: UUID
    to_warehouse_id: UUID
    items: list[dict]  # [{product_id, quantity}]
    note: str | None = None


class ProductCreate(BaseModel):
    name: str
    sku: str
    category_id: UUID | None = None
    unit_of_measure_id: UUID | None = None
    cost_price: Decimal = Decimal("0")
    sale_price: Decimal = Decimal("0")
    reorder_level: Decimal = Decimal("0")
    valuation_method: str = "weighted_average"
