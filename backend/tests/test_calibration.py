import uuid

from fastapi.testclient import TestClient


def _register_login(
    client: TestClient, email: str, role: str = "employee", team_id: str | None = None
) -> str:
    body = {"email": email, "password": "password123", "full_name": f"User {email}", "role": role}
    if team_id is not None:
        body["team_id"] = team_id
    client.post("/auth/register", json=body)
    return client.post(
        "/auth/login", json={"email": email, "password": "password123"}
    ).json()["access_token"]


def _me_id(client: TestClient, token: str) -> str:
    return client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["id"]


# --- user directory ---


def test_users_directory_requires_reviewer(client: TestClient):
    token = _register_login(client, "plain@example.com")
    r = client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_users_directory_team_lead_scoped(client: TestClient):
    team_a = str(uuid.uuid4())
    team_b = str(uuid.uuid4())
    _register_login(client, "a1@example.com", team_id=team_a)
    _register_login(client, "b1@example.com", team_id=team_b)
    lead = _register_login(client, "lead@example.com", role="team_lead", team_id=team_a)

    rows = client.get("/users", headers={"Authorization": f"Bearer {lead}"}).json()
    emails = {u["email"] for u in rows}
    assert "a1@example.com" in emails
    assert "b1@example.com" not in emails


def test_users_directory_hr_sees_all(client: TestClient):
    _register_login(client, "x1@example.com")
    hr = _register_login(client, "hr_dir@example.com", role="hr")
    rows = client.get("/users", headers={"Authorization": f"Bearer {hr}"}).json()
    assert len(rows) >= 2


# --- calibration review ---


def test_create_review_forbidden_for_employee(client: TestClient):
    subject = _register_login(client, "subj_r@example.com")
    subject_id = _me_id(client, subject)
    intruder = _register_login(client, "intr_r@example.com")
    r = client.post(
        "/calibration/review",
        json={"subject_user_id": subject_id, "risk_level": "high"},
        headers={"Authorization": f"Bearer {intruder}"},
    )
    assert r.status_code == 403


def test_hr_creates_review_subject_can_read(client: TestClient):
    subject = _register_login(client, "subj_ok@example.com")
    subject_id = _me_id(client, subject)
    hr = _register_login(client, "hr_rev@example.com", role="hr")

    r = client.post(
        "/calibration/review",
        json={
            "subject_user_id": subject_id,
            "risk_level": "medium",
            "recommendation": "Снизить нагрузку",
            "source_of_evidence": "Опросник 30 дней",
        },
        headers={"Authorization": f"Bearer {hr}"},
    )
    assert r.status_code == 201
    assert r.json()["reviewer_name"] == "User hr_rev@example.com"
    assert r.json()["risk_level"] == "medium"

    # Subject reads reviews about themselves (transparency).
    own = client.get(
        f"/calibration/review/{subject_id}",
        headers={"Authorization": f"Bearer {subject}"},
    )
    assert own.status_code == 200
    assert len(own.json()) == 1
    assert own.json()[0]["recommendation"] == "Снизить нагрузку"


def test_team_lead_cannot_review_other_team(client: TestClient):
    team_a = str(uuid.uuid4())
    team_b = str(uuid.uuid4())
    subject = _register_login(client, "subj_b@example.com", team_id=team_b)
    subject_id = _me_id(client, subject)
    lead_a = _register_login(client, "lead_a@example.com", role="team_lead", team_id=team_a)

    r = client.post(
        "/calibration/review",
        json={"subject_user_id": subject_id, "risk_level": "low"},
        headers={"Authorization": f"Bearer {lead_a}"},
    )
    assert r.status_code == 403


def test_other_employee_cannot_read_reviews(client: TestClient):
    subject = _register_login(client, "subj_priv@example.com")
    subject_id = _me_id(client, subject)
    other = _register_login(client, "nosy@example.com")
    r = client.get(
        f"/calibration/review/{subject_id}",
        headers={"Authorization": f"Bearer {other}"},
    )
    assert r.status_code == 403
