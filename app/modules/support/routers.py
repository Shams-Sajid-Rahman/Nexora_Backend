"""Support routers."""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.crud import make_crud_router
from app.common.serializers import serialize
from app.core.deps import get_current_company, require_permission
from app.db.session import get_db
from . import services
from .models import SupportTicket, TicketMessage
from .schemas import TicketCreate, TicketMessageCreate

router = APIRouter(prefix="/api/v1/support", tags=["support"])


@router.post("/tickets", status_code=201, dependencies=[Depends(require_permission("support.ticket.create"))])
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db), company=Depends(get_current_company)):
    data = payload.model_dump()
    data["customer_id"] = UUID(data["customer_id"]) if data.get("customer_id") else None
    ticket = services.create_ticket(db, company.id, **data)
    return {"data": serialize(ticket), "meta": None}


@router.post("/tickets/{ticket_id}/messages", dependencies=[Depends(require_permission("support.ticket.update"))])
def add_message(ticket_id: UUID, payload: TicketMessageCreate, db: Session = Depends(get_db), company=Depends(get_current_company)):
    from app.common.helpers import get_company_scoped
    ticket = get_company_scoped(db, SupportTicket, ticket_id, company.id)
    msg = TicketMessage(ticket_id=ticket.id, body=payload.body, is_internal=payload.is_internal)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {"data": serialize(msg), "meta": None}


@router.post("/tickets/{ticket_id}/close", dependencies=[Depends(require_permission("support.ticket.update"))])
def close(ticket_id: UUID, db: Session = Depends(get_db), company=Depends(get_current_company)):
    t = services.close_ticket(db, company.id, ticket_id)
    return {"data": serialize(t), "meta": None}


ticket_router = make_crud_router(SupportTicket, prefix="/api/v1/support/tickets-list", permission="support.ticket", name="SupportTicket")
routers = [router, ticket_router]
