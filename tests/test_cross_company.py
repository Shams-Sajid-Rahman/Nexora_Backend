"""Cross-company isolation: another company's record is 404, never data."""
from app.modules.core.services import create_company, register_user


def test_cross_company_record_is_404(auth, client, db_session):
    # Second company + a product in it, owned by the admin of company 1
    # (admin is made a member of company 2 by the test setup below).
    from app.modules.inventory.models import Product
    from app.modules.core.models import UserCompany
    admin = db_session.query(__import__("app.modules.core.models", fromlist=["User"]).User).filter_by(email="admin@nexora.demo").first()
    company2 = create_company(db_session, admin, "Second Co", "second-co", "USD", "Asia/Dhaka")
    product = Product(company_id=company2.id, name="Secret", sku="S-1")
    db_session.add(product)
    db_session.commit()
    # Admin of company 1 asks for company 2's product by id: must be 404.
    r = auth["client"].get(f"/api/v1/inventory/products/{product.id}", headers=auth["headers"])
    assert r.status_code == 404, r.text
    assert "Secret" not in r.text


def test_unauthenticated_is_401(client):
    assert client.get("/api/v1/finance/journal-entries").status_code == 401
    assert client.get("/api/v1/dashboard/overview").status_code == 401
