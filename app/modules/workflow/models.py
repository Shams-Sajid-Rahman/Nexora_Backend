"""Workflow models — docs/04 Workflow."""
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class Workflow(Base, TimestampMixin):
    __tablename__ = "workflows"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(64), nullable=False)
    definition: Mapped[dict | None] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ApprovalRequest(Base, TimestampMixin):
    __tablename__ = "approval_requests"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("workflows.id"))
    entity_type: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))


class ApprovalStep(Base, TimestampMixin):
    __tablename__ = "approval_steps"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    approval_request_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("approval_requests.id"), nullable=False, index=True)
    step_order: Mapped[int] = mapped_column(Integer, default=0)
    approver_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    comment: Mapped[str | None] = mapped_column(Text)


class WorkflowExecutionLog(Base):
    __tablename__ = "workflow_execution_logs"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    workflow_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("workflows.id"), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    outcome: Mapped[str] = mapped_column(String(64), nullable=False)
    detail: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
