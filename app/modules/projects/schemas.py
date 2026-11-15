"""Project schemas."""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    code: str
    budget: Decimal = Decimal("0")
    start_date: date | None = None
    end_date: date | None = None


class TaskCreate(BaseModel):
    title: str
    status: str = "todo"
    priority: str = "medium"
    due_date: date | None = None
