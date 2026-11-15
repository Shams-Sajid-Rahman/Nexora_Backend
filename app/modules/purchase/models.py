"""Purchase models — docs/04 Purchase."""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid

Money = Numeric(19, 4)
Rate = Numeric(19, 6)


class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32))
    address: Mapped[str | None] = mapped_column(Text)
    tax_id: Mapped[str | None] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class PurchaseRequest(Base, TimestampMixin):
    __tablename__ = "purchase_requests"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))


class PurchaseRequestItem(Base):
    __tablename__ = "purchase_request_items"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    request_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("purchase_requests.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("products.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Money, nullable=False)
    estimated_price: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))


class PurchaseOrder(Base, TimestampMixin):
    __tablename__ = "purchase_orders"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("suppliers.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    currency: Mapped[str] = mapped_column(String(3), default="BDT")
    exchange_rate_snapshot: Mapped[Decimal] = mapped_column(Rate, default=Decimal("1"))
    total: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    order_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("purchase_orders.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("products.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Money, nullable=False)
    received_quantity: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    unit_price: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))


class GoodsReceipt(Base, TimestampMixin):
    __tablename__ = "goods_receipts"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    order_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("purchase_orders.id"), nullable=False, index=True)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("warehouses.id"), nullable=False)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))


class GoodsReceiptItem(Base):
    __tablename__ = "goods_receipt_items"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    receipt_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("goods_receipts.id"), nullable=False, index=True)
    order_item_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("purchase_order_items.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Money, nullable=False)
