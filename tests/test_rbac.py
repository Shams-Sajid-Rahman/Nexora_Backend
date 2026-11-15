"""RBAC: a user without a permission gets 403; the error shape matches docs/06."""
from uuid import UUID

from app.modules.core.services import register_user


def test_forbidden_without_permission(client, db_session, auth):
    # A second user in the same company, with no roles at all.
    user = register_user(db_session, "plain@nexora.demo", "Password123!", "Plain User")
    from app.modules.core.models import UserCompany
    db_session.add(UserCompany(user_id=user.id, company_id=UUID(auth["company_id"])))
    db_session.commit()
    from conftest import login
    tokens = login(client, "plain@nexora.demo", "Password123!")
    headers = {"Authorization": f"Bearer {tokens['access_token']}",
               "X-Company-Id": auth["company_id"]}
    r = client.get("/api/v1/finance/journal-entries", headers=headers)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"


def test_admin_can_list_journals(auth):
    r = auth["client"].get("/api/v1/finance/journal-entries", headers=auth["headers"])
    assert r.status_code == 200, r.text
    assert r.json()["data"] == []
    assert r.json()["meta"]["total"] == 0
