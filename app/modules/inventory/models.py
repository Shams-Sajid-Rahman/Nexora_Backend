"""Inventory models — docs/04 Inventory. stock_movements is append-only."""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid

Money = Numeric(19, 4)


class ProductCategory(Base, TimestampMixin):
    __tablename__ = "product_categories"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("product_categories.id"))


class UnitOfMeasure(Base, TimestampMixin):
    __tablename__ = "units_of_measure"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)


class Product(Base, TimestampMixin):
    __tablename__ = "products"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("product_categories.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    unit_of_measure_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("units_of_measure.id"))
    cost_price: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    sale_price: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    reorder_level: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    valuation_method: Mapped[str] = mapped_column(String(32), default="weighted_average")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (Index("ix_products_company_sku", "company_id", "sku", unique=True),)


class Warehouse(Base, TimestampMixin):
    __tablename__ = "warehouses"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("branches.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)


class WarehouseLocation(Base, TimestampMixin):
    __tablename__ = "warehouse_locations"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("warehouses.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)


class StockMovement(Base):
    """Append-only ledger. Never update or delete rows."""
    __tablename__ = "stock_movements"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("products.id"), nullable=False, index=True)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("warehouses.id"), nullable=False, index=True)
    location_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("warehouse_locations.id"))
    movement_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # receipt|issue|transfer_in|transfer_out|adjustment
    quantity: Mapped[Decimal] = mapped_column(Money, nullable=False)  # signed: +in, -out
    unit_cost: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    reference_type: Mapped[str | None] = mapped_column(String(64))
    reference_id: Mapped[str | None] = mapped_column(String(64))
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)


class StockBalance(Base):
    __tablename__ = "stock_balances"
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("products.id"), primary_key=True)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("warehouses.id"), primary_key=True)
    # NULL location is stored as the nil UUID so the PK stays usable.
    location_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=lambda: uuid.UUID(int=0))
    quantity: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class StockTransfer(Base, TimestampMixin):
    __tablename__ = "stock_transfers"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    from_warehouse_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("warehouses.id"), nullable=False)
    to_warehouse_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("warehouses.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    note: Mapped[str | None] = mapped_column(Text)


class StockTransferItem(Base):
    __tablename__ = "stock_transfer_items"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    transfer_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("stock_transfers.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("products.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Money, nullable=False)


class InventoryValuation(Base):
    __tablename__ = "inventory_valuation"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("products.id"), nullable=False)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("warehouses.id"), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    unit_cost: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    total_value: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
