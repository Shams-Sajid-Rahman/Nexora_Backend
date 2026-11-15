"""AI services: forecasting + anomaly detection over real aggregates.

Forecast: simple moving-average of monthly posted invoice totals.
Anomaly: z-score (|x-mean|/std > 2) over the same series.
Both are labelled AI-generated; neither writes business data.
"""
import statistics
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session


def _monthly_invoice_totals(db: Session, company_id: UUID) -> list[float]:
    from app.modules.finance.models import Invoice
    rows = db.query(func.strftime("%Y-%m", Invoice.date), func.sum(Invoice.total)).filter(
        Invoice.company_id == company_id, Invoice.status == "posted"
    ).group_by(func.strftime("%Y-%m", Invoice.date)).order_by(func.strftime("%Y-%m", Invoice.date)).all()
    # strftime is SQLite-specific; on PostgreSQL use to_char — see note in
    # README. Fall back to a Python grouping if the query returns nothing
    # because the dialect differs.
    if rows:
        return [float(v or 0) for _, v in rows]
    invoices = db.query(Invoice).filter(Invoice.company_id == company_id, Invoice.status == "posted").all()
    by_month: dict[str, Decimal] = {}
    for inv in invoices:
        key = inv.date.strftime("%Y-%m")
        by_month[key] = by_month.get(key, Decimal("0")) + (inv.total or Decimal("0"))
    return [float(by_month[k]) for k in sorted(by_month)]


def forecast_sales(db: Session, company_id: UUID, months: int = 3) -> dict:
    series = _monthly_invoice_totals(db, company_id)
    if not series:
        return {"method": "moving_average_3m", "forecast_next_months": [],
                "note": "[AI-generated] No posted invoices yet — no forecast possible."}
    window = series[-3:]
    avg = sum(window) / len(window)
    return {"method": "moving_average_3m", "history_months": len(series),
            "forecast_next_months": [round(avg, 2) for _ in range(months)],
            "note": "[AI-generated] Moving-average forecast from posted invoices only."}


def detect_anomalies(db: Session, company_id: UUID) -> dict:
    series = _monthly_invoice_totals(db, company_id)
    if len(series) < 3:
        return {"method": "z_score_2", "anomalies": [],
                "note": "[AI-generated] Need at least 3 months of posted invoices."}
    mean = statistics.mean(series)
    std = statistics.pstdev(series) or 1.0
    anomalies = [{"month_index": i, "value": v, "z_score": round((v - mean) / std, 2)}
                 for i, v in enumerate(series) if abs((v - mean) / std) > 2]
    return {"method": "z_score_2", "mean": round(mean, 2), "std": round(std, 2),
            "anomalies": anomalies,
            "note": "[AI-generated] Z-score anomaly detection over posted invoice totals."}


def ask(db: Session, user, company_id: UUID, conversation_id: UUID, content: str,
        tool_name: str | None = None) -> dict:
    """Run an approved read-only tool (if requested), log it, and return
    a labelled answer. Sensitive actions are never executed here."""
    from .models import AiActionLog, AiMessage, AiToolCall
    from .providers import get_provider
    from .tools import run_tool
    db.add(AiMessage(conversation_id=conversation_id, role="user", content=content))
    tool_result = None
    if tool_name:
        tool_result = run_tool(db, user, company_id, tool_name)
        db.add(AiToolCall(conversation_id=conversation_id, tool_name=tool_name,
                          arguments={}, result_summary=str(tool_result)[:500]))
        db.add(AiActionLog(company_id=company_id, user_id=user.id, action=f"ai.tool.{tool_name}",
                           entity_type="ai_conversation", entity_id=str(conversation_id),
                           was_executed=False))  # read-only: nothing was executed
    provider = get_provider()
    reply = provider.complete([{"role": "user", "content": content}])
    text = reply["content"]
    if tool_result is not None:
        text += f"\n\nVerified data (read-only tool '{tool_name}'): {tool_result}"
    db.add(AiMessage(conversation_id=conversation_id, role="assistant", content=text, is_ai_generated=True))
    db.commit()
    return {"reply": text, "tool_result": tool_result, "ai_generated": True,
            "provider": provider.name}
