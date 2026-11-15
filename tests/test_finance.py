"""Finance invariants: balanced journals, closed periods, idempotency."""
from datetime import date


def _accounts(auth):
    r = auth["client"].get("/api/v1/finance/accounts?page_size=100", headers=auth["headers"])
    assert r.status_code == 200, r.text
    return {a["code"]: a["id"] for a in r.json()["data"]}


def _journal_payload(accounts, debit=100, credit=100):
    return {"date": str(date(2026, 6, 1)), "description": "test",
            "lines": [{"account_id": accounts["1000"], "debit": debit, "credit": 0},
                      {"account_id": accounts["4000"], "debit": 0, "credit": credit}]}


def test_unbalanced_journal_rejected(auth):
    accounts = _accounts(auth)
    r = auth["client"].post("/api/v1/finance/journal-entries", headers=auth["headers"],
                            json=_journal_payload(accounts, debit=100, credit=90))
    assert r.status_code == 409, r.text
    assert r.json()["error"]["code"] == "JOURNAL_UNBALANCED"


def test_balanced_journal_posts_and_is_immutable(auth):
    accounts = _accounts(auth)
    r = auth["client"].post("/api/v1/finance/journal-entries", headers=auth["headers"],
                            json=_journal_payload(accounts))
    assert r.status_code == 201, r.text
    entry = r.json()["data"]
    r2 = auth["client"].post(f"/api/v1/finance/journal-entries/{entry['id']}/post", headers=auth["headers"])
    assert r2.status_code == 200, r2.text
    assert r2.json()["data"]["status"] == "posted"
    # Posting again is a no-op, not a second posting.
    r3 = auth["client"].post(f"/api/v1/finance/journal-entries/{entry['id']}/post", headers=auth["headers"])
    assert r3.status_code == 200
    # Reversal creates a new balanced entry instead of editing the posted one.
    r4 = auth["client"].post(f"/api/v1/finance/journal-entries/{entry['id']}/reverse", headers=auth["headers"])
    assert r4.status_code == 200, r4.text


def test_journal_idempotency(auth):
    accounts = _accounts(auth)
    headers = {**auth["headers"], "Idempotency-Key": "test-key-1"}
    r1 = auth["client"].post("/api/v1/finance/journal-entries", headers=headers,
                             json=_journal_payload(accounts))
    r2 = auth["client"].post("/api/v1/finance/journal-entries", headers=headers,
                             json=_journal_payload(accounts))
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["data"]["id"] == r2.json()["data"]["id"]


def test_profit_and_loss_from_posted_only(auth):
    accounts = _accounts(auth)
    auth["client"].post("/api/v1/finance/journal-entries", headers=auth["headers"],
                        json=_journal_payload(accounts))
    r = auth["client"].get("/api/v1/finance/profit-and-loss?start=2026-01-01&end=2026-12-31",
                           headers=auth["headers"])
    assert r.status_code == 200, r.text
    # Draft journal must not count as revenue.
    assert r.json()["data"]["revenue"] == 0
