"""Integration endpoints added after the parallel build (Phase 16).

Covers the frontend contract: dashboard summary shape, financial and
generic report kinds, and the AI conversation list.
"""
from conftest import login


def test_dashboard_summary_shape(auth):
    c, h = auth["client"], auth["headers"]
    r = c.get("/api/v1/dashboard/summary", headers=h)
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    for key in ("revenue", "expenses", "returns", "currency", "sales_series",
                "tasks", "inventory", "top_products", "finance"):
        assert key in d, f"missing {key} in dashboard summary"
    assert d["currency"] == "BDT"
    assert isinstance(d["sales_series"], list) and len(d["sales_series"]) == 6
    assert d["finance"]["income"] == d["revenue"]


def test_dashboard_overview_still_works(auth):
    c, h = auth["client"], auth["headers"]
    r = c.get("/api/v1/dashboard/overview", headers=h)
    assert r.status_code == 200, r.text
    assert "revenue_posted_invoices" in r.json()["data"]


def test_financial_reports(auth):
    c, h = auth["client"], auth["headers"]
    for kind in ("profit-and-loss", "balance-sheet", "cash-flow"):
        r = c.get(f"/api/v1/reports/{kind}?from=2026-01-01&to=2026-12-31", headers=h)
        assert r.status_code == 200, (kind, r.text)
        d = r.json()["data"]
        assert "rows" in d and "total" in d, kind


def test_generic_reports(auth):
    c, h = auth["client"], auth["headers"]
    for kind in ("purchases", "hr", "payroll", "projects", "support", "sales", "inventory"):
        r = c.get(f"/api/v1/reports/{kind}?from=2026-01-01&to=2026-12-31", headers=h)
        assert r.status_code == 200, (kind, r.text)


def test_ai_conversations_list_and_create(auth):
    c, h = auth["client"], auth["headers"]
    r = c.post("/api/v1/ai/conversations", json={"title": "test"}, headers=h)
    assert r.status_code == 201, r.text
    r = c.get("/api/v1/ai/conversations", headers=h)
    assert r.status_code == 200, r.text
    assert len(r.json()["data"]) >= 1


def test_dashboard_requires_auth(client):
    r = client.get("/api/v1/dashboard/summary")
    assert r.status_code in (401, 403)
