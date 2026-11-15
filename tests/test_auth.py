"""Auth: login, refresh rotation, reuse detection, logout, bad login."""
from conftest import login


def test_login_ok(client):
    data = login(client)
    assert data["access_token"] and data["refresh_token"]
    assert data["company_id"]


def test_login_wrong_password_is_generic(client):
    r = client.post("/api/v1/auth/login", json={"email": "admin@nexora.demo", "password": "wrong-password"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"


def test_me_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_refresh_rotates_and_old_token_is_rejected(client):
    data = login(client)
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert r.status_code == 200, r.text
    new = r.json()["data"]
    assert new["refresh_token"] != data["refresh_token"]
    # Old (revoked) token must now fail — reuse detection.
    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert r2.status_code == 401


def test_logout_revokes(client):
    data = login(client)
    assert client.post("/api/v1/auth/logout", json={"refresh_token": data["refresh_token"]}).status_code == 200
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert r.status_code == 401
