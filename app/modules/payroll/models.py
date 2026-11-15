"""Payroll models — docs/04 Payroll. Money is NUMERIC(19,4)."""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid

Money = Numeric(19, 4)


class SalaryStructure(Base, TimestampMixin):
    __tablename__ = "salary_structures"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class SalaryComponent(Base, TimestampMixin):
    __tablename__ = "salary_components"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    structure_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("salary_structures.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    # earning | allowance | deduction
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    # fixed | percentage (percentage is of the structure base amount)
    calculation_type: Mapped[str] = mapped_column(String(32), default="fixed")
    amount: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class EmployeeSalary(Base, TimestampMixin):
    __tablename__ = "employee_salaries"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    employee_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("employees.id"), nullable=False, index=True)
    structure_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("salary_structures.id"), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)


class PayrollRun(Base, TimestampMixin):
    __tablename__ = "payroll_runs"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    # draft | calculating | pending_approval | approved | posted
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    posted_journal_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("journal_entries.id"))


class PayrollItem(Base, TimestampMixin):
    __tablename__ = "payroll_items"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    run_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("payroll_runs.id"), nullable=False, index=True)
    employee_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("employees.id"), nullable=False, index=True)
    gross: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    deductions: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    net: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    breakdown: Mapped[dict | None] = mapped_column(JSON)


class Payslip(Base, TimestampMixin):
    __tablename__ = "payslips"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    run_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("payroll_runs.id"), nullable=False, index=True)
    employee_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("employees.id"), nullable=False, index=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
