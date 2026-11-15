"""Support schemas."""
from pydantic import BaseModel


class TicketCreate(BaseModel):
    category: str
    title: str
    description: str | None = None
    priority: str = "medium"
    customer_id: str | None = None


class TicketMessageCreate(BaseModel):
    body: str
    is_internal: bool = False
