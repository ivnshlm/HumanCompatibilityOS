import uuid

from fastapi.testclient import TestClient

from app.onboarding import FRICTION_THRESHOLD, compute_onboarding_health
from app.scoring import compute_burnout_score

from conftest import promote_role


def _res(value: int):
    return compute_burnout_score({i: value for i in range(1, 16)})


def _answers(value: int) -> list[dict]:
    return [{"question_index": i, "value": value} for i in range(1, 16)]


def _register_login(
    client: TestClient, email: str, role: str = "employee", team_id: str | None = None, *, consent: bool = True
) -> str:
    body = {"email": email, "password": "password123", "full_name": f"U {email}", "role": role}
    if team_id is not None:
        body["team_id"] = team_id
    client.post("/auth/register", json=body)
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


# --- Unit: onboarding health ---


def test_onboarding_suppressed_below_cohort():
    health = compute_onboarding_health([_res(3), _res(3)], [])  # 2 < MIN_COHORT
    assert health.sufficient_data is False
    assert health.new_hire_mean is None


def test_onboarding_friction_detected():
    # New hires much hotter (value 5 ~ 4.03) than tenured (value 2 ~ 2.48).
    health = compute_onboarding_health([_res(5)] * 3, [_res(2)] * 3)
    assert health.sufficient_data is True
    assert health.new_hire_mean > health.tenured_mean
    assert health.integration_friction > FRICTION_THRESHOLD
    assert health.friction_flag is True


def test_onboarding_no_tenured_baseline():
    health = compute_onboarding_health([_res(3)] * 3, [])
    assert health.sufficient_data is True
    assert health.tenured_mean is None
    assert health.integration_friction is None
    assert health.friction_flag is False


# --- API ---


def test_onboarding_requires_reviewer(client: TestClient):
    team_id = str(uuid.uuid4())
    token = _register_login(client, "emp_ob@example.com", team_id=team_id)
    r = client.get(f"/onboarding/team/{team_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_onboarding_endpoint_new_hires(client: TestClient):
    team_id = str(uuid.uuid4())
    hr = _register_login(client, "hr_ob@example.com", role="hr")

    # All test users are created "now" => all count as new hires.
    for n in range(3):
        tok = _register_login(client, f"nh{n}@example.com", team_id=team_id)
        client.post(
            "/questionnaire/submit",
            json={"answers": _answers(3)},
            headers={"Authorization": f"Bearer {tok}"},
        )

    r = client.get(f"/onboarding/team/{team_id}", headers={"Authorization": f"Bearer {hr}"})
    assert r.status_code == 200
    body = r.json()
    assert body["sufficient_data"] is True
    assert body["cohort_size"] == 3
    assert body["window_days"] == 90
    # No tenured members in a fresh test DB.
    assert body["tenured_mean"] is None
    assert body["new_hire_mean"] is not None
