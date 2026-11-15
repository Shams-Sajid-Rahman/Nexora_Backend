"""HR models — docs/04 HR."""
import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class Employee(Base, TimestampMixin):
    __tablename__ = "employees"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("branches.id"))
    department_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("departments.id"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    employee_code: Mapped[str] = mapped_column(String(64), nullable=False)
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    designation: Mapped[str | None] = mapped_column(String(128))
    employment_type: Mapped[str] = mapped_column(String(32), default="full_time")
    joined_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EmployeeProfile(Base, TimestampMixin):
    __tablename__ = "employee_profiles"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    employee_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("employees.id"), nullable=False, unique=True)
    address: Mapped[str | None] = mapped_column(Text)
    emergency_contact_name: Mapped[str | None] = mapped_column(String(255))
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(32))
    bank_account: Mapped[str | None] = mapped_column(String(64))
    bank_name: Mapped[str | None] = mapped_column(String(128))


class EmployeeContract(Base, TimestampMixin):
    __tablename__ = "employee_contracts"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    employee_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("employees.id"), nullable=False, index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    designation: Mapped[str | None] = mapped_column(String(128))
    salary_snapshot: Mapped[dict | None] = mapped_column(JSON)


class AttendanceRecord(Base, TimestampMixin):
    __tablename__ = "attendance_records"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    employee_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("employees.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    check_in: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    check_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="present")
    source: Mapped[str] = mapped_column(String(32), default="manual")


class LeaveType(Base, TimestampMixin):
    __tablename__ = "leave_types"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    days_per_year: Mapped[int] = mapped_column(default=0)
    is_paid: Mapped[bool] = mapped_column(default=True)


class LeaveRequest(Base, TimestampMixin):
    __tablename__ = "leave_requests"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    employee_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("employees.id"), nullable=False, index=True)
    leave_type_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("leave_types.id"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    reason: Mapped[str | None] = mapped_column(Text)


class RecruitmentJob(Base, TimestampMixin):
    __tablename__ = "recruitment_jobs"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    department_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("departments.id"))
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    description: Mapped[str | None] = mapped_column(Text)


class JobApplication(Base, TimestampMixin):
    __tablename__ = "job_applications"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    job_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("recruitment_jobs.id"), nullable=False, index=True)
    candidate_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="received", index=True)
    resume_document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
