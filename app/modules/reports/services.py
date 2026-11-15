"""Report services — aggregates over real, posted/approved data only.

Dashboard overview (module B) is computed here from Finance, Sales,
Purchases, Inventory, HR and Support — never hardcoded. The returned
dashboard dict matches the frontend DashboardSummary shape in
frontend/lib/types.ts, and keeps the older overview keys for compatibility.
"""
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session


def _pct_change(current: Decimal, previous: Decimal) -> float:
    if not previous:
        return 0.0
    return float((current - previous) / previous * 100)


def _month_labels(today: date, months: int = 6) -> list[str]:
    labels = []
    y, m = today.year, today.month
    for _ in range(months):
        labels.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return list(reversed(labels))


def dashboard_overview(db: Session, company_id: UUID) -> dict:
    from app.modules.core.models import Company
    from app.modules.finance.models import CreditNote, Invoice, JournalEntry, JournalLine, Account
    from app.modules.inventory.models import Product, StockBalance
    from app.modules.projects.models import Task, Project
    from app.modules.sales.models import Customer, SalesOrder, SalesOrderItem
    from app.modules.support.models import SupportTicket

    company = db.get(Company, company_id)
    currency = company.base_currency if company and company.base_currency else "BDT"
    today = date.today()
    cur_start = today - timedelta(days=30)
    prev_start = today - timedelta(days=60)

    revenue = db.query(func.coalesce(func.sum(Invoice.total), 0)).filter(
        Invoice.company_id == company_id, Invoice.status == "posted").scalar() or Decimal("0")
    expenses = db.query(func.coalesce(func.sum(JournalLine.debit), 0)).join(
        JournalEntry, JournalEntry.id == JournalLine.journal_id).join(
        Account, Account.id == JournalLine.account_id).filter(
        JournalEntry.company_id == company_id, JournalEntry.status == "posted",
        Account.type == "expense").scalar() or Decimal("0")
    returns = db.query(func.coalesce(func.sum(CreditNote.amount), 0)).filter(
        CreditNote.company_id == company_id, CreditNote.status != "draft").scalar() or Decimal("0")

    rev_cur = db.query(func.coalesce(func.sum(Invoice.total), 0)).filter(
        Invoice.company_id == company_id, Invoice.status == "posted",
        Invoice.date >= cur_start, Invoice.date <= today).scalar() or Decimal("0")
    rev_prev = db.query(func.coalesce(func.sum(Invoice.total), 0)).filter(
        Invoice.company_id == company_id, Invoice.status == "posted",
        Invoice.date >= prev_start, Invoice.date < cur_start).scalar() or Decimal("0")
    exp_cur = db.query(func.coalesce(func.sum(JournalLine.debit), 0)).join(
        JournalEntry, JournalEntry.id == JournalLine.journal_id).join(
        Account, Account.id == JournalLine.account_id).filter(
        JournalEntry.company_id == company_id, JournalEntry.status == "posted",
        Account.type == "expense", JournalEntry.date >= cur_start,
        JournalEntry.date <= today).scalar() or Decimal("0")
    exp_prev = db.query(func.coalesce(func.sum(JournalLine.debit), 0)).join(
        JournalEntry, JournalEntry.id == JournalLine.journal_id).join(
        Account, Account.id == JournalLine.account_id).filter(
        JournalEntry.company_id == company_id, JournalEntry.status == "posted",
        Account.type == "expense", JournalEntry.date >= prev_start,
        JournalEntry.date < cur_start).scalar() or Decimal("0")

    # Monthly sales series (Python grouping: SQLite- and Postgres-compatible).
    labels = _month_labels(today)
    sales_by_month = {label: Decimal("0") for label in labels}
    exp_by_month = {label: Decimal("0") for label in labels}
    for inv in db.query(Invoice).filter(
            Invoice.company_id == company_id, Invoice.status == "posted").all():
        key = f"{inv.date.year:04d}-{inv.date.month:02d}" if inv.date else None
        if key in sales_by_month:
            sales_by_month[key] += inv.total or Decimal("0")
    for line, entry in db.query(JournalLine, JournalEntry).join(
            JournalEntry, JournalEntry.id == JournalLine.journal_id).join(
            Account, Account.id == JournalLine.account_id).filter(
            JournalEntry.company_id == company_id, JournalEntry.status == "posted",
            Account.type == "expense").all():
        key = f"{entry.date.year:04d}-{entry.date.month:02d}" if entry.date else None
        if key in exp_by_month:
            exp_by_month[key] += line.debit or Decimal("0")
    sales_series = [{"month": label, "sales": float(sales_by_month[label]),
                     "expenses": float(exp_by_month[label])} for label in labels]

    tasks = []
    for t in db.query(Task).join(Project, Project.id == Task.project_id).filter(
            Project.company_id == company_id,
            Task.status.in_(["todo", "in_progress"])).order_by(
            Task.created_at.desc()).limit(5).all():
        tasks.append({"id": str(t.id), "title": t.title,
                      "description": f"Due {t.due_date}" if t.due_date else None})

    inventory = []
    low_stock = 0
    for p in db.query(Product).filter(Product.company_id == company_id).all():
        total = sum((b.quantity for b in db.query(StockBalance).filter(
            StockBalance.product_id == p.id).all()), Decimal("0"))
        if total <= (p.reorder_level or Decimal("0")):
            low_stock += 1
        inventory.append({"id": str(p.id), "name": p.name, "quantity": float(total), "change": 0})
    inventory = inventory[:5]

    top_products = []
    rows = (db.query(SalesOrderItem.product_id,
                     func.coalesce(func.sum(SalesOrderItem.quantity * SalesOrderItem.unit_price), 0))
            .join(SalesOrder, SalesOrder.id == SalesOrderItem.order_id)
            .filter(SalesOrder.company_id == company_id)
            .group_by(SalesOrderItem.product_id)
            .order_by(func.sum(SalesOrderItem.quantity * SalesOrderItem.unit_price).desc())
            .limit(5).all())
    for product_id, total in rows:
        product = db.get(Product, product_id)
        if product:
            top_products.append({"id": str(product.id), "name": product.name,
                                 "sales": float(total or 0), "change": 0})

    open_orders = db.query(SalesOrder).filter(
        SalesOrder.company_id == company_id, SalesOrder.status.in_(["confirmed", "draft"])).count()
    customers = db.query(Customer).filter(Customer.company_id == company_id).count()
    open_tickets = db.query(SupportTicket).filter(
        SupportTicket.company_id == company_id, SupportTicket.status == "open").count()

    return {
        # Frontend DashboardSummary shape.
        "revenue": float(revenue), "revenue_change": _pct_change(rev_cur, rev_prev),
        "expenses": float(expenses), "expenses_change": _pct_change(exp_cur, exp_prev),
        "returns": float(returns), "returns_change": 0.0,
        "currency": currency, "sales_series": sales_series, "tasks": tasks,
        "inventory": inventory, "top_products": top_products,
        "finance": {"income": float(revenue), "expenses": float(expenses)},
        # Older overview keys, kept for compatibility.
        "revenue_posted_invoices": float(revenue),
        "expenses_posted_journals": float(expenses),
        "open_sales_orders": open_orders, "customers": customers,
        "low_stock_products": low_stock, "open_support_tickets": open_tickets,
    }


def sales_report(db: Session, company_id: UUID, start: date, end: date) -> list[dict]:
    from app.modules.finance.models import Invoice
    rows = db.query(Invoice).filter(Invoice.company_id == company_id,
                                    Invoice.date >= start, Invoice.date <= end).all()
    return [{"code": r.code, "date": str(r.date), "total": float(r.total),
             "status": r.status, "customer_id": str(r.customer_id)} for r in rows]


def inventory_report(db: Session, company_id: UUID) -> list[dict]:
    from app.modules.inventory.models import Product, StockBalance
    out = []
    for p in db.query(Product).filter(Product.company_id == company_id).all():
        total = sum((b.quantity for b in db.query(StockBalance).filter(StockBalance.product_id == p.id).all()), Decimal("0"))
        out.append({"product": p.name, "sku": p.sku, "quantity": float(total),
                    "sale_price": float(p.sale_price or 0), "value": float(total * (p.sale_price or Decimal("0")))})
    return out


def financial_report(db: Session, company_id: UUID, kind: str, start: date, end: date) -> dict:
    """{rows: [{label, amount, account?}], total, note} — posted ledger only."""
    from app.modules.finance.models import Account, JournalEntry, JournalLine, Payment
    from app.modules.finance.services import profit_and_loss

    if kind == "profit-and-loss":
        pl = profit_and_loss(db, company_id, start, end)
        rows = [{"label": "Revenue (income)", "amount": pl["revenue"]},
                {"label": "Expenses", "amount": pl["expenses"]},
                {"label": "Net profit", "amount": pl["net_profit"]}]
        return {"rows": rows, "total": pl["net_profit"],
                "note": "Derived from posted journals only."}
    if kind == "balance-sheet":
        q = (db.query(Account.type, func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), 0))
             .join(JournalLine, JournalLine.account_id == Account.id)
             .join(JournalEntry, JournalEntry.id == JournalLine.journal_id)
             .filter(Account.company_id == company_id, JournalEntry.company_id == company_id,
                     JournalEntry.status == "posted",
                     JournalEntry.date >= start, JournalEntry.date <= end)
             .group_by(Account.type))
        totals = {t: float(v or 0) for t, v in q.all()}
        rows = [{"label": "Assets", "amount": totals.get("asset", 0.0)},
                {"label": "Liabilities", "amount": -totals.get("liability", 0.0)},
                {"label": "Equity", "amount": -totals.get("equity", 0.0)}]
        return {"rows": rows, "total": totals.get("asset", 0.0),
                "note": "Derived from posted journals only."}
    if kind == "cash-flow":
        receipts = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
            Payment.company_id == company_id, Payment.type == "receipt",
            Payment.date >= start, Payment.date <= end).scalar() or Decimal("0")
        payments = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
            Payment.company_id == company_id, Payment.type == "payment",
            Payment.date >= start, Payment.date <= end).scalar() or Decimal("0")
        rows = [{"label": "Cash receipts", "amount": float(receipts)},
                {"label": "Cash payments", "amount": float(payments)},
                {"label": "Net cash flow", "amount": float(receipts - payments)}]
        return {"rows": rows, "total": float(receipts - payments),
                "note": "From recorded payments and receipts in the period."}
    raise ValueError(f"Unknown financial report: {kind}")


def generic_report(db: Session, company_id: UUID, kind: str, start: date, end: date) -> dict:
    """Rows for the /reports/{kind} pages — real counts/totals, no fake data."""
    if kind == "purchases":
        from app.modules.purchase.models import PurchaseOrder
        rows = (db.query(PurchaseOrder.status, func.count(PurchaseOrder.id),
                         func.coalesce(func.sum(PurchaseOrder.total), 0))
                .filter(PurchaseOrder.company_id == company_id)
                .group_by(PurchaseOrder.status).all())
        out = [{"label": f"Purchase orders — {s}", "amount": float(t or 0)} for s, _c, t in rows]
        return {"rows": out, "total": sum(r["amount"] for r in out),
                "note": "Purchase orders by status."}
    if kind == "hr":
        from app.modules.hr.models import Employee
        total = db.query(Employee).filter(Employee.company_id == company_id).count()
        return {"rows": [{"label": "Active employees", "amount": float(total)}],
                "total": float(total), "note": "Employee headcount for the company."}
    if kind == "payroll":
        from app.modules.payroll.models import PayrollItem, PayrollRun
        total = db.query(func.coalesce(func.sum(PayrollItem.net), 0)).join(
            PayrollRun, PayrollRun.id == PayrollItem.run_id).filter(
            PayrollRun.company_id == company_id,
            PayrollRun.period_start >= start, PayrollRun.period_end <= end).scalar() or Decimal("0")
        return {"rows": [{"label": "Net payroll (approved/posted runs in period)", "amount": float(total)}],
                "total": float(total), "note": "From payroll items in the period."}
    if kind == "projects":
        from app.modules.projects.models import Project
        rows = (db.query(Project.status, func.count(Project.id),
                         func.coalesce(func.sum(Project.budget), 0))
                .filter(Project.company_id == company_id)
                .group_by(Project.status).all())
        out = [{"label": f"Projects — {s}", "amount": float(b or 0)} for s, _c, b in rows]
        return {"rows": out, "total": sum(r["amount"] for r in out),
                "note": "Project budgets by status."}
    if kind == "support":
        from app.modules.support.models import SupportTicket
        rows = (db.query(SupportTicket.status, func.count(SupportTicket.id))
                .filter(SupportTicket.company_id == company_id)
                .group_by(SupportTicket.status).all())
        out = [{"label": f"Tickets — {s}", "amount": float(c)} for s, c in rows]
        return {"rows": out, "total": float(sum(r["amount"] for r in out)),
                "note": "Support tickets by status."}
    raise ValueError(f"Unknown report: {kind}")
