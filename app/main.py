"""Nexora FastAPI application.

Response envelope (docs/06): success {"data": ..., "meta": ...},
error {"error": {"code", "message", "details"}}. No stack traces leak.
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import get_logger
from app.db.session import SessionLocal

logger = get_logger("nexora.main")

app = FastAPI(title="Nexora", description="General-Purpose AI-Powered ERP System",
              version="0.1.0", docs_url="/docs", openapi_url="/api/v1/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)


def _error_response(status: int, code: str, message: str, details=None):
    return JSONResponse(status_code=status, content={
        "error": {"code": code, "message": message, "details": details}})


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError):
    return _error_response(exc.status_code, exc.code, exc.message, exc.details)


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError):
    details = [{"field": ".".join(str(p) for p in e["loc"]), "message": e["msg"]}
               for e in exc.errors()]
    return _error_response(422, "VALIDATION_ERROR", "Request validation failed", details)


@app.exception_handler(StarletteHTTPException)
async def http_handler(_: Request, exc: StarletteHTTPException):
    code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
    return _error_response(exc.status_code, code, str(exc.detail))


@app.exception_handler(Exception)
async def unhandled_handler(_: Request, exc: Exception):
    logger.exception("Unhandled error: %s", exc)
    return _error_response(500, "INTERNAL_ERROR", "An internal error occurred")


@app.get("/health")
def health():
    return {"data": {"status": "ok", "app": settings.app_name}, "meta": None}


@app.get("/health/ready")
def ready():
    from sqlalchemy import text
    db_ok, redis_ok = False, False
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:  # noqa: BLE001 - readiness probe
        logger.warning("DB not ready: %s", exc)
    try:
        import redis as redis_lib
        client = redis_lib.Redis.from_url(settings.redis_url, socket_connect_timeout=1)
        redis_ok = bool(client.ping())
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis not ready: %s", exc)
    status = "ready" if db_ok else "not_ready"
    return {"data": {"status": status, "database": db_ok, "redis": redis_ok}, "meta": None}


# Routers — one package per module.
from app.modules.ai.routers import routers as ai_routers  # noqa: E402
from app.modules.core.routers import routers as core_routers  # noqa: E402
from app.modules.finance.routers import routers as finance_routers  # noqa: E402
from app.modules.hr.routers import routers as hr_routers  # noqa: E402
from app.modules.inventory.routers import routers as inventory_routers  # noqa: E402
from app.modules.payroll.routers import routers as payroll_routers  # noqa: E402
from app.modules.projects.routers import routers as project_routers  # noqa: E402
from app.modules.purchase.routers import routers as purchase_routers  # noqa: E402
from app.modules.reports.routers import routers as report_routers  # noqa: E402
from app.modules.sales.routers import routers as sales_routers  # noqa: E402
from app.modules.support.routers import routers as support_routers  # noqa: E402
from app.modules.workflow.routers import routers as workflow_routers  # noqa: E402

for _routers in (core_routers, hr_routers, payroll_routers, inventory_routers,
                 purchase_routers, sales_routers, finance_routers, project_routers,
                 support_routers, report_routers, workflow_routers, ai_routers):
    for _r in _routers:
        app.include_router(_r)
