"""Workflow schemas."""
from pydantic import BaseModel


class WorkflowCreate(BaseModel):
    name: str
    trigger_type: str
    definition: dict | None = None


class ApprovalSubmit(BaseModel):
    entity_type: str
    entity_id: str
    approver_ids: list[str] = []


class ApprovalDecision(BaseModel):
    comment: str | None = None
