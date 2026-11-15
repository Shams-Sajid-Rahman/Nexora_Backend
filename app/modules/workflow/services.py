"""Workflow services. Approvals are logged; a workflow can never silently
approve a sensitive operation — a human decision is always recorded."""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.common.helpers import get_company_scoped
from app.core.audit import log_audit
from app.core.errors import ConflictError
from .models import ApprovalRequest, ApprovalStep, WorkflowExecutionLog


def submit_for_approval(db: Session, company_id: UUID, user_id: UUID, *,
                        workflow_id: UUID | None, entity_type: str, entity_id: str,
                        approver_ids: list[str]) -> ApprovalRequest:
    req = ApprovalRequest(company_id=company_id, workflow_id=workflow_id,
                          entity_type=entity_type, entity_id=entity_id,
                          status="pending", requested_by=user_id)
    db.add(req)
    db.flush()
    for i, approver in enumerate(approver_ids):
        db.add(ApprovalStep(approval_request_id=req.id, step_order=i,
                            approver_id=UUID(approver), status="pending"))
    db.commit()
    db.refresh(req)
    return req


def decide(db: Session, company_id: UUID, user_id: UUID, request_id: UUID,
           approve: bool, comment: str | None = None) -> ApprovalRequest:
    req = get_company_scoped(db, ApprovalRequest, request_id, company_id)
    if req.status != "pending":
        raise ConflictError("Approval request is not pending")
    step = db.query(ApprovalStep).filter(
        ApprovalStep.approval_request_id == req.id,
        ApprovalStep.approver_id == user_id,
        ApprovalStep.status == "pending").order_by(ApprovalStep.step_order).first()
    if step is None:
        raise ConflictError("No pending approval step for this user")
    step.status = "approved" if approve else "rejected"
    step.decided_at = datetime.now(timezone.utc)
    step.comment = comment
    remaining = db.query(ApprovalStep).filter(
        ApprovalStep.approval_request_id == req.id, ApprovalStep.status == "pending").count()
    if not approve:
        req.status = "rejected"
    elif remaining == 0:
        req.status = "approved"
    log_audit(db, action="workflow.approval.decide", entity_type="approval_request",
              entity_id=req.id, user_id=user_id, company_id=company_id,
              after={"decision": step.status})
    db.add(WorkflowExecutionLog(workflow_id=req.workflow_id, entity_type=req.entity_type,
                                entity_id=req.entity_id, outcome=step.status,
                                detail={"by": str(user_id)}))
    db.commit()
    db.refresh(req)
    return req
