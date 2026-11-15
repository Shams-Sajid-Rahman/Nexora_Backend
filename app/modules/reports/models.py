"""Report models — docs/04 Reports. Exports are metadata only; files
live in authorised storage (or are generated on demand)."""
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class SavedReport(Base, TimestampMixin):
    __tablename__ = "saved_reports"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    report_type: Mapped[str] = mapped_column(String(64), nullable=False)
    filters: Mapped[dict | None] = mapped_column(JSON)


class ReportExport(Base, TimestampMixin):
    __tablename__ = "report_exports"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    report_type: Mapped[str] = mapped_column(String(64), nullable=False)
    format: Mapped[str] = mapped_column(String(16), default="csv")  # csv|pdf
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    storage_key: Mapped[str | None] = mapped_column(String(512))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
