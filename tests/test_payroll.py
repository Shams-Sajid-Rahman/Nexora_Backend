"""Payroll: calculation from structures/components, approval gate."""
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from app.modules.hr.models import Employee
from app.modules.payroll.models import EmployeeSalary, SalaryComponent, SalaryStructure
from app.modules.payroll.services import calculate_employee


def test_calculate_employee_pure():
    comps = [
        SalaryComponent(name="Basic", type="earning", calculation_type="fixed", amount=Decimal("1000")),
        SalaryComponent(name="Housing", type="allowance", calculation_type="percentage", amount=Decimal("10")),
        SalaryComponent(name="Tax", type="deduction", calculation_type="percentage", amount=Decimal("5")),
    ]
    result = calculate_employee(uuid4(), comps)
    # base = 1000 fixed earnings; housing 10% = 100; gross 1100; tax 5% of 1000 = 50
    assert result["gross"] == Decimal("1100")
    assert result["deductions"] == Decimal("50")
    assert result["net"] == Decimal("1050")


def test_payroll_run_requires_approval_before_payslips(auth, db_session):
    company_id = UUID(auth["company_id"])
    emp = Employee(company_id=company_id, employee_code="E1", first_name="A", last_name="B",
                   email="a@b.demo")
    db_session.add(emp)
    struct = SalaryStructure(company_id=company_id, name="Standard")
    db_session.add(struct)
    db_session.flush()
    db_session.add(SalaryComponent(structure_id=struct.id, name="Basic", type="earning",
                                   calculation_type="fixed", amount=Decimal("2000")))
    db_session.add(EmployeeSalary(employee_id=emp.id, structure_id=struct.id,
                                  effective_from=date(2026, 1, 1)))
    db_session.commit()
    c = auth["client"]
    run = c.post("/api/v1/payroll/runs", headers=auth["headers"],
                 json={"period_start": "2026-06-01", "period_end": "2026-06-30"}).json()["data"]
    # Payslips before approval must fail.
    r = c.post(f"/api/v1/payroll/runs/{run['id']}/payslips", headers=auth["headers"])
    assert r.status_code == 409, r.text
    # Calculate, approve, then payslips succeed.
    assert c.post(f"/api/v1/payroll/runs/{run['id']}/calculate", headers=auth["headers"]).status_code == 200
    assert c.post(f"/api/v1/payroll/runs/{run['id']}/approve", headers=auth["headers"]).status_code == 200
    r = c.post(f"/api/v1/payroll/runs/{run['id']}/payslips", headers=auth["headers"])
    assert r.status_code == 200, r.text
    assert len(r.json()["data"]) == 1
    items = c.get(f"/api/v1/payroll/runs/{run['id']}/items", headers=auth["headers"]).json()["data"]
    assert items[0]["gross"] == 2000
    assert items[0]["net"] == 2000
