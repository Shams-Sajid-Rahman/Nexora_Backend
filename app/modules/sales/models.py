"""Sales/CRM models — docs/04 Sales. A quotation is NOT a sale."""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid

Money = Numeric(19, 4)
Rate = Numeric(19, 6)


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32))
    address: Mapped[str | None] = mapped_column(Text)
    credit_limit: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CustomerContact(Base, TimestampMixin):
    __tablename__ = "customer_contacts"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    customer_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("customers.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str | None] = mapped_column(String(128))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32))


class Lead(Base, TimestampMixin):
    __tablename__ = "leads"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    source: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="new", index=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))


class Opportunity(Base, TimestampMixin):
    __tablename__ = "opportunities"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("customers.id"))
    lead_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("leads.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    stage: Mapped[str] = mapped_column(String(64), default="prospecting", index=True)
    value: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    probability: Mapped[int] = mapped_column(default=0)
    expected_close_date: Mapped[date | None] = mapped_column(Date)


class Quotation(Base, TimestampMixin):
    __tablename__ = "quotations"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("customers.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    currency: Mapped[str] = mapped_column(String(3), default="BDT")
    exchange_rate_snapshot: Mapped[Decimal] = mapped_column(Rate, default=Decimal("1"))
    total: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))


class QuotationItem(Base):
    __tablename__ = "quotation_items"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    quotation_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("quotations.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("products.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Money, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))


class SalesOrder(Base, TimestampMixin):
    __tablename__ = "sales_orders"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("customers.id"), nullable=False, index=True)
    quotation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("quotations.id"))
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    currency: Mapped[str] = mapped_column(String(3), default="BDT")
    total: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))


class SalesOrderItem(Base):
    __tablename__ = "sales_order_items"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    order_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("sales_orders.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("products.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Money, nullable=False)
    fulfilled_quantity: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    unit_price: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))


class CustomerActivity(Base, TimestampMixin):
    __tablename__ = "customer_activities"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    customer_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("customers.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
