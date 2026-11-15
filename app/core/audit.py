"""Append-only audit logging helper (docs/05 §5.6)."""
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

SENSITIVE_KEYS = {"password", "password_hash", "token", "secret", "api_key"}


def _redact(data: dict | None) -> dict | None:
    if not data:
        return data
    return {k: "***" if k.lower() in SENSITIVE_KEYS else v for k, v in data.items()}


def log_audit(db: Session, *, action: str, entity_type: str,
              entity_id: UUID | str | None = None,
              user_id: UUID | None = None, company_id: UUID | None = None,
              before: dict | None = None, after: dict | None = None,
              ip_address: str | None = None, user_agent: str | None = None) -> None:
    # Local import to avoid a cycle (models import Base only, audit is core).
    from app.modules.core.models import AuditLog
    db.add(AuditLog(
        company_id=company_id, user_id=user_id, action=action,
        entity_type=entity_type, entity_id=str(entity_id) if entity_id else None,
        before=_redact(before), after=_redact(after),
        ip_address=ip_address, user_agent=user_agent,
    ))


def audit_dict(obj: Any, fields: list[str]) -> dict:
    return {f: getattr(obj, f, None) for f in fields if hasattr(obj, f)}
