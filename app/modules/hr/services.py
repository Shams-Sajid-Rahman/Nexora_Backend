"""HR services: leave balances are derived, never hand-edited."""
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.common.helpers import get_company_scoped
from app.core.errors import ConflictError
from .models import Employee, LeaveRequest, LeaveType


def leave_balance(db: Session, company_id: UUID, employee_id: UUID, leave_type_id: UUID) -> dict:
    employee = get_company_scoped(db, Employee, employee_id, company_id)
    leave_type = db.get(LeaveType, leave_type_id)
    if leave_type is None or leave_type.company_id != company_id:
        raise ConflictError("Leave type not found")
    approved = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == employee.id,
        LeaveRequest.leave_type_id == leave_type_id,
        LeaveRequest.status == "approved").all()
    used_days = sum((r.end_date - r.start_date).days + 1 for r in approved)
    return {"employee_id": str(employee.id), "leave_type": leave_type.name,
            "entitled": leave_type.days_per_year, "used": used_days,
            "remaining": leave_type.days_per_year - used_days}


def approve_leave(db: Session, company_id: UUID, user_id: UUID, request_id: UUID) -> LeaveRequest:
    req = db.get(LeaveRequest, request_id)
    if req is None:
        raise ConflictError("Leave request not found")
    employee = db.get(Employee, req.employee_id)
    if employee is None or employee.company_id != company_id:
        raise ConflictError("Leave request not found")
    if req.status != "pending":
        raise ConflictError("Leave request is not pending")
    balance = leave_balance(db, company_id, req.employee_id, req.leave_type_id)
    days = (req.end_date - req.start_date).days + 1
    if days > balance["remaining"]:
        raise ConflictError("Leave request exceeds remaining balance")
    req.status = "approved"
    req.approved_by = user_id
    db.commit()
    db.refresh(req)
    return req
