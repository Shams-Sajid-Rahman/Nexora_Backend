"""Approved read-only AI business tools (docs/05 §5.9).

The LLM may only invoke these tools. Every tool validates company scope
and the caller's permissions, and is logged in ai_tool_calls. There is
NO tool that posts, approves, or modifies salaries or money.
"""
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError

READ_ONLY_TOOLS = ["dashboard_summary", "sales_summary", "finance_summary",
                   "inventory_summary", "forecast_sales", "detect_anomalies"]


def _check(db: Session, user, company_id: UUID, permission: str):
    from app.core.deps import _user_has_permission
    if not _user_has_permission(db, user, company_id, permission):
        raise ForbiddenError(f"Missing permission for AI tool: {permission}")


def dashboard_summary(db: Session, user, company_id: UUID) -> dict:
    _check(db, user, company_id, "reports.view")
    from app.modules.reports.services import dashboard_overview
    return dashboard_overview(db, company_id)


def sales_summary(db: Session, user, company_id: UUID) -> dict:
    _check(db, user, company_id, "sales.order.view")
    from datetime import date, timedelta
    from app.modules.reports.services import sales_report
    end = date.today()
    return {"rows": sales_report(db, company_id, end - timedelta(days=30), end)}


def finance_summary(db: Session, user, company_id: UUID) -> dict:
    _check(db, user, company_id, "finance.report.view")
    from datetime import date
    from app.modules.finance.services import profit_and_loss
    end = date.today()
    return profit_and_loss(db, company_id, date(end.year, 1, 1), end)


def inventory_summary(db: Session, user, company_id: UUID) -> dict:
    _check(db, user, company_id, "inventory.stock.view")
    from app.modules.inventory.services import low_stock_products
    from app.modules.reports.services import inventory_report
    return {"low_stock": low_stock_products(db, company_id),
            "items": inventory_report(db, company_id)[:50]}


TOOLS = {
    "dashboard_summary": dashboard_summary,
    "sales_summary": sales_summary,
    "finance_summary": finance_summary,
    "inventory_summary": inventory_summary,
}


def run_tool(db: Session, user, company_id: UUID, tool_name: str, arguments: dict | None = None) -> dict:
    if tool_name in ("forecast_sales", "detect_anomalies"):
        from .services import forecast_sales, detect_anomalies
        _check(db, user, company_id, "reports.view")
        if tool_name == "forecast_sales":
            return forecast_sales(db, company_id)
        return detect_anomalies(db, company_id)
    fn = TOOLS.get(tool_name)
    if fn is None:
        raise ForbiddenError(f"AI tool not approved: {tool_name}")
    return fn(db, user, company_id)
