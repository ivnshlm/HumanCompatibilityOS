import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.deps import require_roles
from app.models import Role, User


def _register(client: TestClient, email: str, role: str = "employee", password: str = "password123"):
    return client.post(
        "/auth/register",
        json={"email": email, "password": password, "full_name": "Test User", "role": role},
    )


def test_register_and_login(client: TestClient):
    r = _register(client, "emp@example.com")
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "emp@example.com"
    assert body["role"] == "employee"
    assert body["consent_given"] is False

    r = client.post("/auth/login", json={"email": "emp@example.com", "password": "password123"})
    assert r.status_code == 200
    tokens = r.json()
    assert tokens["access_token"] and tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"


def test_duplicate_email_rejected(client: TestClient):
    assert _register(client, "dup@example.com").status_code == 201
    assert _register(client, "dup@example.com").status_code == 409


def test_login_wrong_password(client: TestClient):
    _register(client, "wrong@example.com")
    r = client.post("/auth/login", json={"email": "wrong@example.com", "password": "nope"})
    assert r.status_code == 401


def test_me_requires_token(client: TestClient):
    assert client.get("/auth/me").status_code == 403  # no bearer credentials


def test_me_with_token(client: TestClient):
    _register(client, "me@example.com")
    tokens = client.post(
        "/auth/login", json={"email": "me@example.com", "password": "password123"}
    ).json()
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert r.status_code == 200
    assert r.json()["email"] == "me@example.com"


def test_refresh_flow(client: TestClient):
    _register(client, "refresh@example.com")
    tokens = client.post(
        "/auth/login", json={"email": "refresh@example.com", "password": "password123"}
    ).json()
    r = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    assert r.json()["access_token"]

    # An access token must not be accepted by the refresh endpoint.
    r = client.post("/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert r.status_code == 401


def test_consent_flow(client: TestClient):
    _register(client, "consent@example.com")
    tokens = client.post(
        "/auth/login", json={"email": "consent@example.com", "password": "password123"}
    ).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    r = client.post("/auth/consent", json={"consent_given": True}, headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["consent_given"] is True
    assert body["consent_at"] is not None


def test_rbac_guard_logic():
    guard = require_roles(Role.hr)
    employee = User(role=Role.employee)
    hr = User(role=Role.hr)

    with pytest.raises(HTTPException) as exc:
        guard(user=employee)
    assert exc.value.status_code == 403

    assert guard(user=hr) is hr
