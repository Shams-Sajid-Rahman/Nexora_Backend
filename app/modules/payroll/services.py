"""Payroll services.

Calculation is from the salary structure in force for the period:
- fixed components add their amount
- percentage components are a percentage of the structure's base amount
  (the sum of fixed earnings), or of gross-to-date for deductions
- payslips are generated ONLY from an approved run
- posting goes through Finance (balanced journal), never direct writes
"""
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.common.helpers import get_company_scoped
from app.core.audit import log_audit
from app.core.errors import ConflictError
from .models import (EmployeeSalary, PayrollItem, PayrollRun, Payslip,
                     SalaryComponent, SalaryStructure)


def calculate_employee(structure_id: UUID, components: list[SalaryComponent]) -> dict:
    """Pure calculation — unit-testable without a database."""
    base = sum((c.amount for c in components if c.calculation_type == "fixed" and c.type in ("earning", "allowance")), Decimal("0"))
    gross = Decimal("0")
    deductions = Decimal("0")
    breakdown: dict[str, float] = {}
    for c in sorted(components, key=lambda x: x.sort_order or 0):
        if c.calculation_type == "percentage":
            value = (base * c.amount / Decimal("100")).quantize(Decimal("0.0001"))
        else:
            value = c.amount
        breakdown[c.name] = float(value)
        if c.type == "deduction":
            deductions += value
        else:
            gross += value
    return {"gross": gross, "deductions": deductions, "net": gross - deductions, "breakdown": breakdown}


def calculate_run(db: Session, company_id: UUID, run_id: UUID) -> PayrollRun:
    run = get_company_scoped(db, PayrollRun, run_id, company_id)
    if run.status not in ("draft", "calculating"):
        raise ConflictError("Payroll run can only be calculated in draft status")
    run.status = "calculating"
    db.flush()
    db.query(PayrollItem).filter(PayrollItem.run_id == run.id).delete()
    assignments = db.query(EmployeeSalary).all()
    # Only assignments whose employee belongs to this company and whose
    # structure is effective for the period.
    from app.modules.hr.models import Employee
    for assignment in assignments:
        employee = db.get(Employee, assignment.employee_id)
        if employee is None or employee.company_id != company_id:
            continue
        if assignment.effective_from > run.period_end:
            continue
        if assignment.effective_to and assignment.effective_to < run.period_start:
            continue
        components = db.query(SalaryComponent).filter(
            SalaryComponent.structure_id == assignment.structure_id).all()
        result = calculate_employee(assignment.structure_id, components)
        db.add(PayrollItem(run_id=run.id, employee_id=employee.id,
                           gross=result["gross"], deductions=result["deductions"],
                           net=result["net"], breakdown=result["breakdown"]))
    run.status = "pending_approval"
    db.commit()
    db.refresh(run)
    return run


def approve_run(db: Session, company_id: UUID, user_id: UUID, run_id: UUID) -> PayrollRun:
    run = get_company_scoped(db, PayrollRun, run_id, company_id)
    if run.status != "pending_approval":
        raise ConflictError("Payroll run must be pending approval before it can be approved")
    run.status = "approved"
    run.approved_by = user_id
    log_audit(db, action="payroll.run.approve", entity_type="payroll_run",
              entity_id=run.id, user_id=user_id, company_id=company_id)
    db.commit()
    db.refresh(run)
    return run


def generate_payslips(db: Session, company_id: UUID, run_id: UUID) -> list[Payslip]:
    run = get_company_scoped(db, PayrollRun, run_id, company_id)
    if run.status not in ("approved", "posted"):
        raise ConflictError("Payslips can only be generated from an approved payroll run")
    items = db.query(PayrollItem).filter(PayrollItem.run_id == run.id).all()
    out = []
    for item in items:
        existing = db.query(Payslip).filter(Payslip.run_id == run.id,
                                            Payslip.employee_id == item.employee_id).first()
        if existing:
            out.append(existing)
            continue
        slip = Payslip(run_id=run.id, employee_id=item.employee_id,
                       issued_at=datetime.now(timezone.utc))
        db.add(slip)
        out.append(slip)
    db.commit()
    return out


def post_run(db: Session, company_id: UUID, user_id: UUID, run_id: UUID) -> PayrollRun:
    run = get_company_scoped(db, PayrollRun, run_id, company_id)
    if run.status != "approved":
        raise ConflictError("Payroll run must be approved before posting")
    items = db.query(PayrollItem).filter(PayrollItem.run_id == run.id).all()
    gross = sum((i.gross for i in items), Decimal("0"))
    deductions = sum((i.deductions for i in items), Decimal("0"))
    net = sum((i.net for i in items), Decimal("0"))
    if gross == 0:
        run.status = "posted"
        db.commit()
        return run
    from app.modules.finance.models import Account
    from app.modules.finance.services import post_balanced_journal
    salary_exp = db.query(Account).filter(Account.company_id == company_id, Account.code == "6000").first()
    payable = db.query(Account).filter(Account.company_id == company_id, Account.code == "2000").first()
    if salary_exp is None or payable is None:
        raise ConflictError("Chart of accounts is incomplete (need 6000 Salary Expense and 2000 AP)")
    journal = post_balanced_journal(
        db, company_id, user_id, entry_date=run.period_end,
        description=f"Payroll {run.period_start} to {run.period_end}",
        lines=[{"account_id": salary_exp.id, "debit": gross, "credit": Decimal("0")},
               {"account_id": payable.id, "debit": Decimal("0"), "credit": net},
               {"account_id": payable.id, "debit": Decimal("0"), "credit": deductions}] if deductions else
              [{"account_id": salary_exp.id, "debit": gross, "credit": Decimal("0")},
               {"account_id": payable.id, "debit": Decimal("0"), "credit": net}],
        source_type="payroll_run", source_id=str(run.id))
    run.status = "posted"
    run.posted_journal_id = journal.id
    db.commit()
    db.refresh(run)
    return run
