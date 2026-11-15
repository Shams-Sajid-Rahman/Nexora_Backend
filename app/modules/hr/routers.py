"""HR routers."""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.crud import make_crud_router
from app.common.serializers import serialize
from app.core.deps import get_current_company, get_current_user, require_permission
from app.db.session import get_db
from . import services
from .models import (AttendanceRecord, Employee, JobApplication, LeaveRequest,
                     LeaveType, RecruitmentJob)
from .schemas import EmployeeCreate, LeaveRequestCreate

router = APIRouter(prefix="/api/v1/hr", tags=["hr"])


@router.post("/employees", status_code=201, dependencies=[Depends(require_permission("hr.employee.create"))])
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db), company=Depends(get_current_company)):
    emp = Employee(company_id=company.id, **payload.model_dump())
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return {"data": serialize(emp), "meta": None}


@router.post("/leave-requests", status_code=201, dependencies=[Depends(require_permission("hr.leave.view"))])
def create_leave(payload: LeaveRequestCreate, db: Session = Depends(get_db), company=Depends(get_current_company)):
    # employee must belong to this company (checked via leave_balance path in approve; here check directly)
    emp = db.get(Employee, payload.employee_id)
    if emp is None or emp.company_id != company.id:
        from app.core.errors import NotFoundError
        raise NotFoundError("Employee not found")
    req = LeaveRequest(**payload.model_dump())
    db.add(req)
    db.commit()
    db.refresh(req)
    return {"data": serialize(req), "meta": None}


@router.post("/leave-requests/{request_id}/approve", dependencies=[Depends(require_permission("hr.leave.approve"))])
def approve_leave(request_id: UUID, db: Session = Depends(get_db),
                  user=Depends(get_current_user), company=Depends(get_current_company)):
    req = services.approve_leave(db, company.id, user.id, request_id)
    return {"data": serialize(req), "meta": None}


@router.get("/employees/{employee_id}/leave-balance/{leave_type_id}")
def leave_balance(employee_id: UUID, leave_type_id: UUID, db: Session = Depends(get_db), company=Depends(get_current_company)):
    return {"data": services.leave_balance(db, company.id, employee_id, leave_type_id), "meta": None}


employee_router = make_crud_router(Employee, prefix="/api/v1/hr/employees-list", permission="hr.employee", name="Employee", code_prefix="EMP")
leave_type_router = make_crud_router(LeaveType, prefix="/api/v1/hr/leave-types", permission="hr.leave", name="LeaveType")
leave_router = make_crud_router(LeaveRequest, prefix="/api/v1/hr/leave-requests-list", permission="hr.leave", name="LeaveRequest")
attendance_router = make_crud_router(AttendanceRecord, prefix="/api/v1/hr/attendance", permission="hr.employee", name="AttendanceRecord")
job_router = make_crud_router(RecruitmentJob, prefix="/api/v1/hr/jobs", permission="hr.employee", name="RecruitmentJob")
application_router = make_crud_router(JobApplication, prefix="/api/v1/hr/applications", permission="hr.employee", name="JobApplication")

routers = [router, employee_router, leave_type_router, leave_router, attendance_router, job_router, application_router]
