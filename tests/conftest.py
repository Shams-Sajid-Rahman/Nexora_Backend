"""Test fixtures: SQLite in-memory DB, seeded demo company + admin.

No live Postgres is needed to run `pytest`.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.db.seed import seed
from app.main import app as fastapi_app

# Import all models so Base.metadata is complete.
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


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = TestingSession()
    seed(session)
    yield session
    session.close()


@pytest.fixture()
def client(db_session):
    def _override():
        try:
            yield db_session
        finally:
            pass
    fastapi_app.dependency_overrides[get_db] = _override
    with TestClient(fastapi_app, raise_server_exceptions=False) as c:
        yield c
    fastapi_app.dependency_overrides.clear()


def login(client, email="admin@nexora.demo", password="Admin123!"):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["data"]


@pytest.fixture()
def auth(client, db_session):
    tokens = login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    if tokens.get("company_id"):
        headers["X-Company-Id"] = tokens["company_id"]
    return {"client": client, "db": db_session, "headers": headers,
            "tokens": tokens, "company_id": tokens["company_id"]}
