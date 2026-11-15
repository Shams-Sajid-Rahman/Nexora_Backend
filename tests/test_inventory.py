"""Inventory: ledger append-only, transactional balances, no negative stock."""
from app.modules.inventory.services import get_balance, record_stock_movement
from app.modules.core.models import Company
import uuid


def _setup(auth):
    c = auth["client"]
    wh = c.post("/api/v1/inventory/warehouses", headers=auth["headers"],
                json={"name": "Test WH", "code": "TWH"}).json()["data"]
    prod = c.post("/api/v1/inventory/products", headers=auth["headers"],
                  json={"name": "Widget", "sku": "W-1", "sale_price": 10}).json()["data"]
    return wh["id"], prod["id"]


def test_stock_receipt_and_issue(auth, db_session):
    wh, prod = _setup(auth)
    c = auth["client"]
    r = c.post("/api/v1/inventory/stock-movements", headers=auth["headers"], json={
        "product_id": prod, "warehouse_id": wh, "movement_type": "receipt",
        "quantity": 10, "unit_cost": 5})
    assert r.status_code == 201, r.text
    assert get_balance(db_session, uuid.UUID(prod), uuid.UUID(wh)) == 10
    r = c.post("/api/v1/inventory/stock-movements", headers=auth["headers"], json={
        "product_id": prod, "warehouse_id": wh, "movement_type": "issue",
        "quantity": -4, "unit_cost": 5})
    assert r.status_code == 201, r.text
    assert get_balance(db_session, uuid.UUID(prod), uuid.UUID(wh)) == 6


def test_negative_stock_rejected(auth):
    wh, prod = _setup(auth)
    r = auth["client"].post("/api/v1/inventory/stock-movements", headers=auth["headers"], json={
        "product_id": prod, "warehouse_id": wh, "movement_type": "issue",
        "quantity": -1, "unit_cost": 5})
    assert r.status_code == 409, r.text
    assert r.json()["error"]["code"] == "INSUFFICIENT_STOCK"


def test_ledger_is_append_only_via_api(auth):
    wh, prod = _setup(auth)
    auth["client"].post("/api/v1/inventory/stock-movements", headers=auth["headers"], json={
        "product_id": prod, "warehouse_id": wh, "movement_type": "receipt", "quantity": 5})
    r = auth["client"].get("/api/v1/inventory/stock-movements", headers=auth["headers"])
    assert r.status_code == 200
    assert len(r.json()["data"]) == 1
    # No update/delete endpoint exists for stock movements (append-only).
    assert r.json()["data"][0]["movement_type"] == "receipt"
