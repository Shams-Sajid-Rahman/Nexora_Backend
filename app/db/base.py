"""SQLAlchemy 2.x declarative base + shared mixins (docs/04 §4.1).

UUID primary keys, UTC timestamps, NUMERIC money, soft delete.
`Uuid` maps to native UUID on PostgreSQL and CHAR(32) on SQLite, so the
same models run in tests (SQLite) and production (PostgreSQL).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class CompanyMixin:
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, index=True)


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()
