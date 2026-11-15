"""Payroll schemas."""
from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class SalaryComponentCreate(BaseModel):
    name: str
    type: str  # earning|allowance|deduction
    calculation_type: str = "fixed"
    amount: Decimal = Decimal("0")
    sort_order: int = 0


class SalaryStructureCreate(BaseModel):
    name: str
    components: list[SalaryComponentCreate] = []


class PayrollRunCreate(BaseModel):
    period_start: date
    period_end: date
    employee_ids: list[UUID] = []
