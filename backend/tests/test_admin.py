import uuid

from fastapi.testclient import TestClient

from conftest import promote_role


def _register(client: TestClient, email: str, role_in_body: str = "employee") -> None:
    # role_in_body is intentionally passed to prove the server ignores it.
    client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "full_name": "U", "role": role_in_body},
    )


def _login(client: TestClient, email: str) -> str:
    return client.post(
        "/auth/login", json={"email": email, "password": "password123"}
    ).json()["access_token"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _admin(client: TestClient, email: str) -> str:
    _register(client, email)
    promote_role(email, "admin")
    return _login(client, email)


def test_registration_ignores_requested_role(client: TestClient):
    # Even asking for admin at registration must yield a plain employee.
    _register(client, "sneaky@example.com", role_in_body="admin")
    token = _login(client, "sneaky@example.com")
    me = client.get("/auth/me", headers=_h(token)).json()
    assert me["role"] == "employee"


def test_bootstrap_email_becomes_admin_on_register(client: TestClient, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "initial_admin_emails", "boss@example.com")
    _register(client, "boss@example.com", role_in_body="employee")
    token = _login(client, "boss@example.com")
    me = client.get("/auth/me", headers=_h(token)).json()
    assert me["role"] == "admin"


def test_admin_endpoints_forbidden_for_non_admin(client: TestClient):
    _register(client, "emp@example.com")
    emp = _login(client, "emp@example.com")
    assert client.get("/admin/users", headers=_h(emp)).status_code == 403

    # HR is a reviewer but NOT an admin — no user management.
    _register(client, "hr@example.com")
    promote_role("hr@example.com", "hr")
    hr = _login(client, "hr@example.com")
    assert client.get("/admin/users", headers=_h(hr)).status_code == 403


def test_admin_lists_and_changes_role(client: TestClient):
    admin = _admin(client, "owner@example.com")
    _register(client, "u1@example.com")
    u1 = client.get("/auth/me", headers=_h(_login(client, "u1@example.com"))).json()["id"]

    rows = client.get("/admin/users", headers=_h(admin)).json()
    assert {"owner@example.com", "u1@example.com"} <= {r["email"] for r in rows}

    r = client.patch(f"/admin/users/{u1}", json={"role": "hr"}, headers=_h(admin))
    assert r.status_code == 200
    assert r.json()["role"] == "hr"


def test_admin_deactivate_blocks_access(client: TestClient):
    admin = _admin(client, "owner2@example.com")
    _register(client, "victim@example.com")
    victim_token = _login(client, "victim@example.com")
    victim_id = client.get("/auth/me", headers=_h(victim_token)).json()["id"]

    r = client.patch(f"/admin/users/{victim_id}", json={"is_active": False}, headers=_h(admin))
    assert r.status_code == 200
    assert r.json()["is_active"] is False

    # Existing token is rejected once the account is deactivated.
    assert client.get("/auth/me", headers=_h(victim_token)).status_code == 401
    # And a fresh login is refused too.
    assert client.post(
        "/auth/login", json={"email": "victim@example.com", "password": "password123"}
    ).status_code == 403


def test_cannot_demote_or_deactivate_last_admin(client: TestClient):
    admin = _admin(client, "solo@example.com")
    solo_id = client.get("/auth/me", headers=_h(admin)).json()["id"]

    demote = client.patch(f"/admin/users/{solo_id}", json={"role": "employee"}, headers=_h(admin))
    assert demote.status_code == 400

    deactivate = client.patch(
        f"/admin/users/{solo_id}", json={"is_active": False}, headers=_h(admin)
    )
    assert deactivate.status_code == 400


def test_admin_404_for_unknown_user(client: TestClient):
    admin = _admin(client, "owner3@example.com")
    r = client.patch(f"/admin/users/{uuid.uuid4()}", json={"role": "hr"}, headers=_h(admin))
    assert r.status_code == 404
