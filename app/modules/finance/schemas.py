"""Finance schemas."""
from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class JournalLineCreate(BaseModel):
    account_id: UUID
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    currency: str = "BDT"
    exchange_rate_snapshot: Decimal = Decimal("1")
    description: str | None = None


class JournalCreate(BaseModel):
    date: date
    description: str | None = None
    period_id: UUID | None = None
    lines: list[JournalLineCreate] = Field(min_length=2)
    idempotency_key: str | None = None


class InvoiceCreate(BaseModel):
    customer_id: UUID
    sales_order_id: UUID | None = None
    date: date
    due_date: date | None = None
    currency: str = "BDT"
    items: list[dict] = []


class PaymentCreate(BaseModel):
    type: str  # receipt|payment
    counterparty_type: str | None = None
    counterparty_id: UUID | None = None
    bank_account_id: UUID | None = None
    amount: Decimal
    currency: str = "BDT"
    date: date
    reference: str | None = None
    allocate_to: list[dict] = []  # [{document_type, document_id, amount}]
    idempotency_key: str | None = None


class AccountCreate(BaseModel):
    code: str
    name: str
    type: str
    parent_id: UUID | None = None
