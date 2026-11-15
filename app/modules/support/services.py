"""Support services: SLA is derived from priority/category policy."""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.common.helpers import get_company_scoped, to_aware
from .models import SlaPolicy, SupportTicket

DEFAULT_SLA_HOURS = {"low": 72, "medium": 48, "high": 24, "urgent": 8}


def sla_due(db: Session, company_id: UUID, priority: str, category: str) -> datetime:
    policy = db.query(SlaPolicy).filter(
        SlaPolicy.company_id == company_id, SlaPolicy.priority == priority,
        SlaPolicy.category == category).first()
    hours = policy.resolution_hours if policy else DEFAULT_SLA_HOURS.get(priority, 48)
    return datetime.now(timezone.utc) + timedelta(hours=hours)


def create_ticket(db: Session, company_id: UUID, **data) -> SupportTicket:
    ticket = SupportTicket(company_id=company_id, **data)
    ticket.sla_due_at = sla_due(db, company_id, ticket.priority, ticket.category)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def close_ticket(db: Session, company_id: UUID, ticket_id: UUID) -> SupportTicket:
    ticket = get_company_scoped(db, SupportTicket, ticket_id, company_id)
    ticket.status = "closed"
    if ticket.sla_due_at and datetime.now(timezone.utc) > to_aware(ticket.sla_due_at):
        ticket.sla_breached = True
    db.commit()
    db.refresh(ticket)
    return ticket
