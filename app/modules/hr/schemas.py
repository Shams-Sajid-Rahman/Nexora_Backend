"""HR schemas."""
from datetime import date
from uuid import UUID

from pydantic import BaseModel, EmailStr


class EmployeeCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    employee_code: str
    branch_id: UUID | None = None
    department_id: UUID | None = None
    designation: str | None = None
    employment_type: str = "full_time"
    joined_date: date | None = None


class LeaveRequestCreate(BaseModel):
    employee_id: UUID
    leave_type_id: UUID
    start_date: date
    end_date: date
    reason: str | None = None


class AttendanceCreate(BaseModel):
    employee_id: UUID
    date: date
    status: str = "present"
