"""Seed a demo company, admin user and chart of accounts.

Idempotent for a fresh database: run once after `alembic upgrade head`.
Demo credentials (change immediately in real use): admin@nexora.demo / Admin123!
"""
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.modules.core.models import Branch, Company, Department, User, UserCompany, UserRole
from app.modules.core.services import create_admin_role, seed_permissions
from app.modules.finance.models import Account, AccountingPeriod, FiscalYear
from app.modules.hr.models import LeaveType
from app.modules.inventory.models import Product, UnitOfMeasure, Warehouse

CHART_OF_ACCOUNTS = [
    ("1000", "Cash", "asset"), ("1100", "Accounts Receivable", "asset"),
    ("1200", "Inventory", "asset"), ("2000", "Accounts Payable", "liability"),
    ("2100", "Salary Payable", "liability"), ("3000", "Owner Capital", "equity"),
    ("4000", "Sales Revenue", "income"), ("5000", "Cost of Goods Sold", "expense"),
    ("6000", "Salary Expense", "expense"), ("6100", "Rent Expense", "expense"),
    ("6200", "Utilities Expense", "expense"),
]


def seed(db: Session) -> dict:
    seed_permissions(db)
    company = db.query(Company).filter(Company.slug == "nexora-demo").first()
    if company is None:
        company = Company(name="Nexora Demo Ltd", slug="nexora-demo",
                          base_currency="BDT", timezone="Asia/Dhaka")
        db.add(company)
        db.flush()
    admin = db.query(User).filter(User.email == "admin@nexora.demo").first()
    if admin is None:
        admin = User(email="admin@nexora.demo", password_hash=get_password_hash("Admin123!"),
                     full_name="Demo Admin")
        db.add(admin)
        db.flush()
    if not db.query(UserCompany).filter(UserCompany.user_id == admin.id,
                                        UserCompany.company_id == company.id).first():
        db.add(UserCompany(user_id=admin.id, company_id=company.id, is_default=True))
    role = create_admin_role(db, company.id)
    if not db.query(UserRole).filter(UserRole.user_id == admin.id,
                                     UserRole.role_id == role.id,
                                     UserRole.company_id == company.id).first():
        db.add(UserRole(user_id=admin.id, role_id=role.id, company_id=company.id))
    branch = db.query(Branch).filter(Branch.company_id == company.id).first()
    if branch is None:
        branch = Branch(company_id=company.id, name="Head Office", code="HQ", is_head_office=True)
        db.add(branch)
        db.flush()
    if not db.query(Department).filter(Department.company_id == company.id).first():
        db.add(Department(company_id=company.id, branch_id=branch.id, name="Operations", code="OPS"))
    for code, name, type_ in CHART_OF_ACCOUNTS:
        if not db.query(Account).filter(Account.company_id == company.id, Account.code == code).first():
            db.add(Account(company_id=company.id, code=code, name=name, type=type_))
    fy = db.query(FiscalYear).filter(FiscalYear.company_id == company.id).first()
    if fy is None:
        fy = FiscalYear(company_id=company.id, name="FY 2026",
                        start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
        db.add(fy)
        db.flush()
        db.add(AccountingPeriod(fiscal_year_id=fy.id, name="2026", start_date=date(2026, 1, 1),
                                end_date=date(2026, 12, 31)))
    for name, days in [("Annual Leave", 20), ("Sick Leave", 10), ("Casual Leave", 10)]:
        if not db.query(LeaveType).filter(LeaveType.company_id == company.id, LeaveType.name == name).first():
            db.add(LeaveType(company_id=company.id, name=name, days_per_year=days, is_paid=True))
    uom = db.query(UnitOfMeasure).filter(UnitOfMeasure.company_id == company.id).first()
    if uom is None:
        uom = UnitOfMeasure(company_id=company.id, name="Piece", symbol="pcs")
        db.add(uom)
        db.flush()
    if not db.query(Warehouse).filter(Warehouse.company_id == company.id).first():
        db.add(Warehouse(company_id=company.id, branch_id=branch.id, name="Main Warehouse", code="WH-01"))
    db.commit()
    return {"company_id": str(company.id), "admin_email": admin.email}


if __name__ == "__main__":
    from app.db.base import Base
    from app.db.session import SessionLocal, engine
    import app.modules.core.models  # noqa: F401
    import app.modules.hr.models  # noqa: F401
    import app.modules.payroll.models  # noqa: F401
    import app.modules.inventory.models  # noqa: F401
    import app.modules.purchase.models  # noqa: F401
    import app.modules.sales.models  # noqa: F401
    import app.modules.finance.models  # noqa: F401
    import app.modules.projects.models  # noqa: F401
    import app.modules.support.models  # noqa: F401
    import app.modules.reports.models  # noqa: F401
    import app.modules.workflow.models  # noqa: F401
    import app.modules.ai.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    print(seed(SessionLocal()))
