"""Workflow routers."""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.crud import make_crud_router
from app.common.serializers import serialize
from app.core.deps import get_current_company, get_current_user, require_permission
from app.db.session import get_db
from . import services
from .models import ApprovalRequest, Workflow
from .schemas import ApprovalDecision, ApprovalSubmit, WorkflowCreate

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])


@router.post("", status_code=201, dependencies=[Depends(require_permission("workflow.create"))])
def create_workflow(payload: WorkflowCreate, db: Session = Depends(get_db), company=Depends(get_current_company)):
    w = Workflow(company_id=company.id, **payload.model_dump())
    db.add(w)
    db.commit()
    db.refresh(w)
    return {"data": serialize(w), "meta": None}


@router.post("/approvals", status_code=201, dependencies=[Depends(require_permission("workflow.create"))])
def submit(payload: ApprovalSubmit, db: Session = Depends(get_db),
           user=Depends(get_current_user), company=Depends(get_current_company)):
    req = services.submit_for_approval(db, company.id, user.id, workflow_id=None,
                                       entity_type=payload.entity_type, entity_id=payload.entity_id,
                                       approver_ids=payload.approver_ids)
    return {"data": serialize(req), "meta": None}


@router.post("/approvals/{request_id}/approve", dependencies=[Depends(require_permission("workflow.approve"))])
def approve(request_id: UUID, payload: ApprovalDecision, db: Session = Depends(get_db),
            user=Depends(get_current_user), company=Depends(get_current_company)):
    req = services.decide(db, company.id, user.id, request_id, True, payload.comment)
    return {"data": serialize(req), "meta": None}


@router.post("/approvals/{request_id}/reject", dependencies=[Depends(require_permission("workflow.approve"))])
def reject(request_id: UUID, payload: ApprovalDecision, db: Session = Depends(get_db),
           user=Depends(get_current_user), company=Depends(get_current_company)):
    req = services.decide(db, company.id, user.id, request_id, False, payload.comment)
    return {"data": serialize(req), "meta": None}


workflow_router = make_crud_router(Workflow, prefix="/api/v1/workflows-list", permission="workflow", name="Workflow")
approval_router = make_crud_router(ApprovalRequest, prefix="/api/v1/workflows/approvals-list", permission="workflow", name="ApprovalRequest")

routers = [router, workflow_router, approval_router]
