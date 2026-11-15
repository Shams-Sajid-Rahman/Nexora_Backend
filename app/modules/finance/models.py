"""Finance models — docs/04 Finance. NUMERIC money, balanced journals."""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid

Money = Numeric(19, 4)
Rate = Numeric(19, 6)


class Account(Base, TimestampMixin):
    __tablename__ = "accounts"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)  # asset|liability|equity|income|expense
    parent_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("accounts.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class FiscalYear(Base, TimestampMixin):
    __tablename__ = "fiscal_years"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)


class AccountingPeriod(Base, TimestampMixin):
    __tablename__ = "accounting_periods"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    fiscal_year_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("fiscal_years.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)


class JournalEntry(Base, TimestampMixin):
    __tablename__ = "journal_entries"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    period_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("accounting_periods.id"))
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)  # draft|posted
    source_type: Mapped[str | None] = mapped_column(String(64))
    source_id: Mapped[str | None] = mapped_column(String(64))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    posted_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    reverses_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("journal_entries.id"))
    idempotency_key: Mapped[str | None] = mapped_column(String(128), index=True)


class JournalLine(Base):
    __tablename__ = "journal_lines"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    journal_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("journal_entries.id"), nullable=False, index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("accounts.id"), nullable=False, index=True)
    debit: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    credit: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(3), default="BDT")
    exchange_rate_snapshot: Mapped[Decimal] = mapped_column(Rate, default=Decimal("1"))
    base_amount: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    description: Mapped[str | None] = mapped_column(Text)


class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("customers.id"), nullable=False, index=True)
    sales_order_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("sales_orders.id"))
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3), default="BDT")
    total: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    paid_total: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)


class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    invoice_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("invoices.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("products.id"))
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    unit_price: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))


class Bill(Base, TimestampMixin):
    __tablename__ = "bills"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("suppliers.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3), default="BDT")
    total: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    paid_total: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)  # receipt|payment
    counterparty_type: Mapped[str | None] = mapped_column(String(32))
    counterparty_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    bank_account_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("bank_accounts.id"))
    amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="BDT")
    date: Mapped[date] = mapped_column(Date, nullable=False)
    reference: Mapped[str | None] = mapped_column(String(128))
    idempotency_key: Mapped[str | None] = mapped_column(String(128), index=True)


class PaymentAllocation(Base):
    __tablename__ = "payment_allocations"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    payment_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("payments.id"), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(32), nullable=False)  # invoice|bill
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Money, nullable=False)


class Expense(Base, TimestampMixin):
    __tablename__ = "expenses"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    employee_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("employees.id"))
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="BDT")
    date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    receipt_document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)


class BankAccount(Base, TimestampMixin):
    __tablename__ = "bank_accounts"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    bank_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_number: Mapped[str] = mapped_column(String(64), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="BDT")
    opening_balance: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))


class BankTransaction(Base, TimestampMixin):
    __tablename__ = "bank_transactions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    bank_account_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("bank_accounts.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)  # debit|credit
    is_reconciled: Mapped[bool] = mapped_column(Boolean, default=False)
    journal_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("journal_entries.id"))


class CreditNote(Base, TimestampMixin):
    __tablename__ = "credit_notes"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("invoices.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)


class ExchangeRate(Base, TimestampMixin):
    """Company exchange rates. Changing a rate never rewrites history:
    posted documents keep their own exchange_rate_snapshot."""
    __tablename__ = "exchange_rates"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    from_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    to_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Rate, nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
