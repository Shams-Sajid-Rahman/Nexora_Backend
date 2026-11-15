"""Sales schemas."""
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class QuotationCreate(BaseModel):
    customer_id: UUID
    currency: str = "BDT"
    items: list[dict] = []  # [{product_id, quantity, unit_price}]


class SalesOrderCreate(BaseModel):
    customer_id: UUID
    quotation_id: UUID | None = None
    currency: str = "BDT"
    items: list[dict] = []


class CustomerCreate(BaseModel):
    name: str
    code: str
    email: str | None = None
    phone: str | None = None
    credit_limit: Decimal = Decimal("0")
