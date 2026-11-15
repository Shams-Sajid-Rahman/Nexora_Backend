"""Support models — docs/04 Support."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class SupportTicket(Base, TimestampMixin):
    __tablename__ = "support_tickets"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("customers.id"))
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(16), default="medium", index=True)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sla_breached: Mapped[bool] = mapped_column(Boolean, default=False)


class TicketMessage(Base, TimestampMixin):
    __tablename__ = "ticket_messages"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    ticket_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("support_tickets.id"), nullable=False, index=True)
    author_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)  # internal notes never shown to customer


class SlaPolicy(Base, TimestampMixin):
    __tablename__ = "sla_policies"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="general")
    response_hours: Mapped[int] = mapped_column(Integer, default=24)
    resolution_hours: Mapped[int] = mapped_column(Integer, default=72)
