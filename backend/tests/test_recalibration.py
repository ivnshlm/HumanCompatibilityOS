from fastapi.testclient import TestClient

from app.recalibration import (
    Trend,
    recommendations_for,
    trend_for,
)
from app.scoring import compute_burnout_score

from conftest import promote_role


def _answers(value: int) -> list[dict]:
    return [{"question_index": i, "value": value} for i in range(1, 16)]


def _register_login(client: TestClient, email: str, role: str = "employee", *, consent: bool = True) -> str:
    client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "full_name": "T", "role": role},
    )
    if role != "employee":
        promote_role(email, role)
    token = client.post(
        "/auth/login", json={"email": email, "password": "password123"}
    ).json()["access_token"]
    if consent:
        client.post(
            "/auth/consent",
            json={"consent_given": True},
            headers={"Authorization": f"Bearer {token}"},
        )
    return token


# --- Unit: trend ---


def test_trend_classification():
    assert trend_for(4.0, 3.0) == Trend.improving  # pressure dropped
    assert trend_for(2.0, 3.0) == Trend.worsening
    assert trend_for(3.0, 3.1) == Trend.stable
    assert trend_for(None, 3.0) == Trend.insufficient
    assert trend_for(3.0, None) == Trend.insufficient


# --- Unit: recommendations ---


def test_recommendations_flag_high_driver():
    result = compute_burnout_score({i: 5 for i in range(1, 16)})  # emergency = 5
    recs = recommendations_for(result)
    assert len(recs) >= 1
    assert any("аврал" in r.lower() for r in recs)


def test_recommendations_general_when_no_driver():
    result = compute_burnout_score({i: 2 for i in range(1, 16)})  # all components < 3.5
    recs = recommendations_for(result)
    assert len(recs) == 1
    assert "норм" in recs[0].lower()


# --- API ---


def test_create_requires_access(client: TestClient):
    subject_token = _register_login(client, "subj@example.com")
    subject_headers = {"Authorization": f"Bearer {subject_token}"}
    subject_id = client.get("/auth/me", headers=subject_headers).json()["id"]
    client.post("/questionnaire/submit", json={"answers": _answers(3)}, headers=subject_headers)

    other_token = _register_login(client, "intruder@example.com")
    r = client.post(
        "/recalibration/create",
        json={"user_id": subject_id, "cycle": "baseline"},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert r.status_code == 403


def test_create_without_questionnaire_rejected(client: TestClient):
    token = _register_login(client, "noq@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    user_id = client.get("/auth/me", headers=headers).json()["id"]
    r = client.post(
        "/recalibration/create",
        json={"user_id": user_id, "cycle": "baseline"},
        headers=headers,
    )
    assert r.status_code == 400


def test_timeline_trend_and_delta(client: TestClient):
    token = _register_login(client, "cycle@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    user_id = client.get("/auth/me", headers=headers).json()["id"]

    # Baseline anchored to a high-pressure questionnaire (explicit id keeps the
    # test deterministic under SQLite's second-resolution timestamps).
    q_high = client.post(
        "/questionnaire/submit", json={"answers": _answers(5)}, headers=headers
    ).json()["id"]
    client.post(
        "/recalibration/create",
        json={"user_id": user_id, "cycle": "baseline", "questionnaire_id": q_high},
        headers=headers,
    )
    # Day-30 anchored to a much healthier questionnaire.
    q_low = client.post(
        "/questionnaire/submit", json={"answers": _answers(1)}, headers=headers
    ).json()["id"]
    r = client.post(
        "/recalibration/create",
        json={"user_id": user_id, "cycle": "day_30", "questionnaire_id": q_low},
        headers=headers,
    )
    assert r.status_code == 201
    assert r.json()["delta_vs_baseline"] is not None
    assert r.json()["delta_vs_baseline"] < 0  # improvement

    timeline = client.get(f"/recalibration/{user_id}", headers=headers).json()
    assert len(timeline["events"]) == 2
    assert timeline["baseline_score"] is not None
    assert timeline["trend"] == "improving"
    assert isinstance(timeline["recommendations"], list)


def test_reviewer_can_create_for_others(client: TestClient):
    subject_token = _register_login(client, "emp_rc@example.com")
    subject_headers = {"Authorization": f"Bearer {subject_token}"}
    subject_id = client.get("/auth/me", headers=subject_headers).json()["id"]
    client.post("/questionnaire/submit", json={"answers": _answers(4)}, headers=subject_headers)

    hr_token = _register_login(client, "hr_rc@example.com", role="hr")
    r = client.post(
        "/recalibration/create",
        json={"user_id": subject_id, "cycle": "baseline"},
        headers={"Authorization": f"Bearer {hr_token}"},
    )
    assert r.status_code == 201
