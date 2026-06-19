import uuid

from fastapi.testclient import TestClient

from app.dashboard import MIN_COHORT, aggregate_team
from app.scoring import compute_burnout_score


def _answers(value: int = 3) -> list[dict]:
    return [{"question_index": i, "value": value} for i in range(1, 16)]


def _register(client: TestClient, email: str, role: str = "employee", team_id: str | None = None) -> str:
    body = {"email": email, "password": "password123", "full_name": "T", "role": role}
    if team_id is not None:
        body["team_id"] = team_id
    client.post("/auth/register", json=body)
    token = client.post(
        "/auth/login", json={"email": email, "password": "password123"}
    ).json()["access_token"]
    return token


def _member_with_submission(client: TestClient, email: str, team_id: str, value: int) -> None:
    token = _register(client, email, team_id=team_id)
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/auth/consent", json={"consent_given": True}, headers=headers)
    client.post("/questionnaire/submit", json={"answers": _answers(value)}, headers=headers)


# --- Unit tests: aggregation ---


def test_aggregate_team_suppresses_small_cohort():
    results = [compute_burnout_score({i: 3 for i in range(1, 16)}) for _ in range(MIN_COHORT - 1)]
    dash = aggregate_team(results)
    assert dash.sufficient_data is False
    assert dash.blocks == []
    assert dash.cohort_size == MIN_COHORT - 1
    assert dash.notice is not None
    # §10: the notice must state the de-anonymization rationale, not just "no data".
    assert "деанонимиз" in dash.notice
    assert str(MIN_COHORT) in dash.notice


def test_aggregate_team_reports_four_blocks():
    results = [compute_burnout_score({i: 3 for i in range(1, 16)}) for _ in range(MIN_COHORT)]
    dash = aggregate_team(results)
    assert dash.sufficient_data is True
    assert {b.block.value for b in dash.blocks} == {
        "burnout_pressure",
        "recovery_sustainability",
        "communication_entropy",
        "leadership_stability",
    }
    # All answers == 3 → every component mean is 3.0 → medium.
    burnout = next(b for b in dash.blocks if b.block.value == "burnout_pressure")
    assert burnout.score == 3.0
    assert burnout.risk_level.value == "medium"
    assert burnout.distribution == {"low": 0, "medium": MIN_COHORT, "high": 0}


# --- API tests ---


def test_dashboard_requires_reviewer_role(client: TestClient):
    team_id = str(uuid.uuid4())
    token = _register(client, "emp@example.com", team_id=team_id)
    r = client.get(f"/dashboard/team/{team_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_dashboard_insufficient_then_sufficient(client: TestClient):
    team_id = str(uuid.uuid4())
    hr_token = _register(client, "hr@example.com", role="hr")
    hr_headers = {"Authorization": f"Bearer {hr_token}"}

    # Only one member → suppressed.
    _member_with_submission(client, "m1@example.com", team_id, 3)
    r = client.get(f"/dashboard/team/{team_id}", headers=hr_headers)
    assert r.status_code == 200
    assert r.json()["sufficient_data"] is False
    assert r.json()["cohort_size"] == 1
    assert r.json()["blocks"] == []

    # Reach the cohort threshold.
    _member_with_submission(client, "m2@example.com", team_id, 4)
    _member_with_submission(client, "m3@example.com", team_id, 2)
    r = client.get(f"/dashboard/team/{team_id}", headers=hr_headers)
    body = r.json()
    assert body["sufficient_data"] is True
    assert body["cohort_size"] == MIN_COHORT
    assert len(body["blocks"]) == 4


def test_dashboard_team_lead_scoped_to_own_team(client: TestClient):
    own_team = str(uuid.uuid4())
    other_team = str(uuid.uuid4())
    lead_token = _register(client, "lead@example.com", role="team_lead", team_id=own_team)
    lead_headers = {"Authorization": f"Bearer {lead_token}"}

    assert client.get(f"/dashboard/team/{own_team}", headers=lead_headers).status_code == 200
    assert client.get(f"/dashboard/team/{other_team}", headers=lead_headers).status_code == 403


def test_environment_metrics_record_and_aggregate(client: TestClient):
    team_id = str(uuid.uuid4())
    hr_token = _register(client, "hr2@example.com", role="hr")
    hr_headers = {"Authorization": f"Bearer {hr_token}"}

    for v in (2.0, 4.0, 6.0):
        r = client.post(
            "/environment/metrics",
            json={"metric_type": "meeting_load", "value": v, "team_id": team_id},
            headers=hr_headers,
        )
        assert r.status_code == 201

    r = client.get(f"/environment/metrics?team_id={team_id}", headers=hr_headers)
    assert r.status_code == 200
    aggs = r.json()["aggregates"]
    assert len(aggs) == 1
    agg = aggs[0]
    assert agg["metric_type"] == "meeting_load"
    assert agg["count"] == 3
    assert agg["mean"] == 4.0
    assert agg["minimum"] == 2.0
    assert agg["maximum"] == 6.0


def test_environment_metrics_record_forbidden_for_employee(client: TestClient):
    token = _register(client, "emp2@example.com")
    r = client.post(
        "/environment/metrics",
        json={"metric_type": "meeting_load", "value": 1.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403
