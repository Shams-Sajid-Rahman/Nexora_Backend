"""Payroll routers."""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.crud import make_crud_router
from app.common.serializers import serialize, serialize_list
from app.core.deps import get_current_company, get_current_user, require_permission
from app.db.session import get_db
from . import services
from .models import PayrollRun, SalaryComponent, SalaryStructure
from .schemas import PayrollRunCreate, SalaryStructureCreate

router = APIRouter(prefix="/api/v1/payroll", tags=["payroll"])


@router.post("/salary-structures", status_code=201, dependencies=[Depends(require_permission("payroll.structure.create"))])
def create_structure(payload: SalaryStructureCreate, db: Session = Depends(get_db), company=Depends(get_current_company)):
    structure = SalaryStructure(company_id=company.id, name=payload.name)
    db.add(structure)
    db.flush()
    for c in payload.components:
        db.add(SalaryComponent(structure_id=structure.id, name=c.name, type=c.type,
                               calculation_type=c.calculation_type, amount=c.amount, sort_order=c.sort_order))
    db.commit()
    db.refresh(structure)
    return {"data": serialize(structure), "meta": None}


@router.post("/runs", status_code=201, dependencies=[Depends(require_permission("payroll.run.create"))])
def create_run(payload: PayrollRunCreate, db: Session = Depends(get_db), company=Depends(get_current_company)):
    run = PayrollRun(company_id=company.id, period_start=payload.period_start, period_end=payload.period_end)
    db.add(run)
    db.commit()
    db.refresh(run)
    return {"data": serialize(run), "meta": None}


@router.post("/runs/{run_id}/calculate", dependencies=[Depends(require_permission("payroll.run.create"))])
def calculate(run_id: UUID, db: Session = Depends(get_db), company=Depends(get_current_company)):
    run = services.calculate_run(db, company.id, run_id)
    return {"data": serialize(run), "meta": None}


@router.post("/runs/{run_id}/approve", dependencies=[Depends(require_permission("payroll.run.approve"))])
def approve(run_id: UUID, db: Session = Depends(get_db),
            user=Depends(get_current_user), company=Depends(get_current_company)):
    run = services.approve_run(db, company.id, user.id, run_id)
    return {"data": serialize(run), "meta": None}


@router.post("/runs/{run_id}/payslips", dependencies=[Depends(require_permission("payroll.run.approve"))])
def payslips(run_id: UUID, db: Session = Depends(get_db), company=Depends(get_current_company)):
    slips = services.generate_payslips(db, company.id, run_id)
    return {"data": serialize_list(slips), "meta": None}


@router.post("/runs/{run_id}/post", dependencies=[Depends(require_permission("payroll.run.post"))])
def post(run_id: UUID, db: Session = Depends(get_db),
         user=Depends(get_current_user), company=Depends(get_current_company)):
    run = services.post_run(db, company.id, user.id, run_id)
    return {"data": serialize(run), "meta": None}


@router.get("/runs/{run_id}/items", dependencies=[Depends(require_permission("payroll.run.view"))])
def run_items(run_id: UUID, db: Session = Depends(get_db), company=Depends(get_current_company)):
    from .models import PayrollItem
    from app.common.helpers import get_company_scoped
    run = get_company_scoped(db, PayrollRun, run_id, company.id)
    items = db.query(PayrollItem).filter(PayrollItem.run_id == run.id).all()
    return {"data": serialize_list(items), "meta": None}


structure_router = make_crud_router(SalaryStructure, prefix="/api/v1/payroll/structures", permission="payroll.structure", name="SalaryStructure")
run_router = make_crud_router(PayrollRun, prefix="/api/v1/payroll/runs-list", permission="payroll.run", name="PayrollRun")

routers = [router, structure_router, run_router]
