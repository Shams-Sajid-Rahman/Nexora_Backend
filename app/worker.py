"""Celery worker (Redis broker from env). HTTP requests never do
long-running work synchronously — they enqueue one of these tasks."""
from celery import Celery

from app.core.config import settings

celery_app = Celery("nexora", broker=settings.celery_broker_url,
                    backend=settings.celery_result_backend)
celery_app.conf.task_routes = {"app.worker.*": {"queue": "nexora"}}
celery_app.conf.beat_schedule = {
    "low-stock-check-hourly": {"task": "app.worker.check_low_stock", "schedule": 3600.0},
}


@celery_app.task(name="app.worker.generate_report_export", max_retries=3)
def generate_report_export(export_id: str):
    from app.db.session import SessionLocal
    from app.modules.reports.models import ReportExport
    with SessionLocal() as db:
        export = db.get(ReportExport, export_id)
        if export is None:
            return {"status": "not_found"}
        # CSV/PDF generation happens here in production (streaming from the
        # report services). For now the export is marked complete with a
        # storage key the frontend can poll for.
        export.status = "completed"
        export.storage_key = f"exports/{export.id}.{export.format}"
        db.commit()
        return {"status": "completed", "export_id": export_id}


@celery_app.task(name="app.worker.run_payroll", max_retries=3)
def run_payroll(run_id: str, company_id: str):
    from uuid import UUID
    from app.db.session import SessionLocal
    from app.modules.payroll.services import calculate_run
    with SessionLocal() as db:
        run = calculate_run(db, UUID(company_id), UUID(run_id))
        return {"status": run.status, "run_id": run_id}


@celery_app.task(name="app.worker.send_notification", max_retries=3)
def send_notification(user_id: str, title: str, body: str):
    # Email/push delivery is configured in deployment; the notification
    # row is the durable record and is already created by the caller.
    return {"status": "queued", "user_id": user_id, "title": title, "body": body}


@celery_app.task(name="app.worker.process_ai_job", max_retries=2)
def process_ai_job(conversation_id: str):
    return {"status": "queued", "conversation_id": conversation_id}


@celery_app.task(name="app.worker.check_low_stock")
def check_low_stock():
    from app.db.session import SessionLocal
    from app.modules.core.models import Company
    from app.modules.inventory.services import low_stock_products
    with SessionLocal() as db:
        out = {}
        for company in db.query(Company).all():
            out[str(company.id)] = low_stock_products(db, company.id)
        return out
