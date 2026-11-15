"""Report + dashboard routers."""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.crud import make_crud_router
from app.core.deps import get_current_company, get_current_user, require_permission
from app.db.session import get_db
from . import services
from .models import ReportExport, SavedReport
from .schemas import ReportExportCreate

router = APIRouter(prefix="/api/v1", tags=["reports"])


@router.get("/dashboard/overview", dependencies=[Depends(require_permission("reports.view"))])
def dashboard(db: Session = Depends(get_db), company=Depends(get_current_company)):
    return {"data": services.dashboard_overview(db, company.id), "meta": None}


@router.get("/dashboard/summary", dependencies=[Depends(require_permission("reports.view"))])
def dashboard_summary(db: Session = Depends(get_db), company=Depends(get_current_company)):
    """Alias used by the frontend dashboard page — same data as /dashboard/overview."""
    return {"data": services.dashboard_overview(db, company.id), "meta": None}


@router.get("/reports/sales", dependencies=[Depends(require_permission("reports.view"))])
def sales_report(db: Session = Depends(get_db), company=Depends(get_current_company),
                 start: date | None = Query(None), end: date | None = Query(None),
                 from_: date | None = Query(None, alias="from"), to: date | None = Query(None)):
    start = start or from_ or date(2000, 1, 1)
    end = end or to or date.today()
    return {"data": services.sales_report(db, company.id, start, end), "meta": None}


@router.get("/reports/inventory", dependencies=[Depends(require_permission("reports.view"))])
def inventory_report(db: Session = Depends(get_db), company=Depends(get_current_company)):
    return {"data": services.inventory_report(db, company.id), "meta": None}


@router.get("/reports/{kind}", dependencies=[Depends(require_permission("reports.view"))])
def generic_or_financial_report(kind: str, db: Session = Depends(get_db),
                                company=Depends(get_current_company),
                                start: date | None = Query(None),
                                end: date | None = Query(None),
                                from_: date | None = Query(None, alias="from"),
                                to: date | None = Query(None)):
    """Frontend /reports/{kind} and /finance/reports/{kind} endpoints.

    Financial kinds (profit-and-loss, balance-sheet, cash-flow) are derived
    from the posted ledger; the others are real aggregates (see services).
    """
    start = start or from_ or date(2000, 1, 1)
    end = end or to or date.today()
    if kind in ("profit-and-loss", "balance-sheet", "cash-flow"):
        return {"data": services.financial_report(db, company.id, kind, start, end), "meta": None}
    if kind in ("purchases", "hr", "payroll", "projects", "support"):
        return {"data": services.generic_report(db, company.id, kind, start, end), "meta": None}
    return {"data": {"rows": [], "total": 0, "note": f"Unknown report: {kind}"}, "meta": None}


@router.post("/reports/exports", status_code=201, dependencies=[Depends(require_permission("reports.export"))])
def request_export(payload: ReportExportCreate, db: Session = Depends(get_db),
                   user=Depends(get_current_user), company=Depends(get_current_company)):
    # The task is queued by Celery in production; here we record it and
    # return pending — the worker marks it complete (see app/worker.py).
    from app.common.serializers import serialize
    export = ReportExport(company_id=company.id, user_id=user.id, report_type=payload.report_type,
                          format=payload.format, status="pending")
    db.add(export)
    db.commit()
    db.refresh(export)
    return {"data": serialize(export), "meta": None}


saved_router = make_crud_router(SavedReport, prefix="/api/v1/reports/saved", permission="reports", name="SavedReport")
export_router = make_crud_router(ReportExport, prefix="/api/v1/reports/exports-list", permission="reports", name="ReportExport")

routers = [router, saved_router, export_router]
