"""Project routers."""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.crud import make_crud_router
from app.common.serializers import serialize
from app.core.deps import get_current_company, require_permission
from app.db.session import get_db
from . import services
from .models import Milestone, Project, Task, Timesheet
from .schemas import ProjectCreate

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.post("", status_code=201, dependencies=[Depends(require_permission("projects.project.create"))])
def create_project(payload: ProjectCreate, db: Session = Depends(get_db), company=Depends(get_current_company)):
    p = Project(company_id=company.id, **payload.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"data": serialize(p), "meta": None}


@router.get("/{project_id}/cost", dependencies=[Depends(require_permission("projects.project.view"))])
def cost(project_id: UUID, db: Session = Depends(get_db), company=Depends(get_current_company)):
    return {"data": services.project_cost(db, company.id, project_id), "meta": None}


project_router = make_crud_router(Project, prefix="/api/v1/projects-list", permission="projects.project", name="Project", code_prefix="PROJ")
task_router = make_crud_router(Task, prefix="/api/v1/projects/tasks", permission="projects.task", name="Task")
milestone_router = make_crud_router(Milestone, prefix="/api/v1/projects/milestones", permission="projects.project", name="Milestone")
timesheet_router = make_crud_router(Timesheet, prefix="/api/v1/projects/timesheets", permission="projects.task", name="Timesheet")

routers = [router, project_router, task_router, milestone_router, timesheet_router]
