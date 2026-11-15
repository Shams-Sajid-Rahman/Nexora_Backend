"""Project services: budget tracking from timesheets + costs."""
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.common.helpers import get_company_scoped
from .models import Project, Timesheet


def project_cost(db: Session, company_id: UUID, project_id: UUID) -> dict:
    project = get_company_scoped(db, Project, project_id, company_id)
    hours = db.query(Timesheet).filter(Timesheet.project_id == project.id).all()
    total_hours = sum((t.hours for t in hours), Decimal("0"))
    return {"project_id": str(project.id), "name": project.name,
            "budget": float(project.budget or 0), "logged_hours": float(total_hours),
            "remaining_budget": float((project.budget or Decimal("0")))}
