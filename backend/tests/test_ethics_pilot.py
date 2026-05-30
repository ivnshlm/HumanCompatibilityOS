import uuid

from fastapi.testclient import TestClient

from app.pilot import PILOT_TARGET_PCT, compute_pilot_report
from app.scoring import compute_burnout_score


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


def _me_id(client: TestClient, token: str) -> str:
    return client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["id"]


def _submit(client: TestClient, token: str, value: int) -> str:
    return client.post(
        "/questionnaire/submit",
        json={"answers": _answers(value)},
        headers={"Authorization": f"Bearer {token}"},
    ).json()["id"]


def _recal(client: TestClient, token: str, user_id: str, cycle: str, qid: str) -> None:
    client.post(
        "/recalibration/create",
        json={"user_id": user_id, "cycle": cycle, "questionnaire_id": qid},
        headers={"Authorization": f"Bearer {token}"},
    )


# --- Unit: pilot metric ---


def test_pilot_report_target_met():
    # Emergency pressure 5.0 -> 1.0 for 3 members = -80% (meets -20%).
    report = compute_pilot_report([(_res(5), _res(1))] * 3)
    assert report.sufficient_data is True
    assert report.target_met is True
    assert report.target_pct == PILOT_TARGET_PCT
    assert report.headline.key == "emergency_pressure"
    assert report.headline.pct_change == -80.0
    assert len(report.blocks) == 4  # all four environment blocks
    assert {b.key for b in report.blocks} == {
        "burnout_pressure",
        "recovery_sustainability",
        "communication_entropy",
        "leadership_stability",
    }


def test_pilot_report_not_met_and_suppressed():
    flat = compute_pilot_report([(_res(3), _res(3))] * 3)  # no change
    assert flat.sufficient_data is True
    assert flat.target_met is False
    suppressed = compute_pilot_report([(_res(5), _res(1))])  # cohort < 3
    assert suppressed.sufficient_data is False
    assert suppressed.headline is None


# --- compliance policy ---


def test_compliance_policy(client: TestClient):
    token = _register_login(client, "anyone@example.com")
    r = client.get("/compliance/policy", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["no_automated_decisions"] is True
    assert body["requires_human_review"] is True
    assert body["pilot_target_pct"] == PILOT_TARGET_PCT
    assert len(body["principles"]) >= 5


# --- audit log access ---


def test_audit_restricted_to_oversight(client: TestClient):
    hr = _register_login(client, "hr_aud@example.com", role="hr")
    assert client.get("/audit", headers={"Authorization": f"Bearer {hr}"}).status_code == 403

    admin = _register_login(client, "admin_aud@example.com", role="admin")
    r = client.get("/audit", headers={"Authorization": f"Bearer {admin}"})
    assert r.status_code == 200
    # Registrations/logins already produced audit rows.
    assert len(r.json()) >= 1


# --- export ---


def test_export_self_and_rbac(client: TestClient):
    subj = _register_login(client, "exp_subj@example.com")
    subj_id = _me_id(client, subj)
    _submit(client, subj, 3)

    own = client.get(
        f"/export/employee/{subj_id}", headers={"Authorization": f"Bearer {subj}"}
    )
    assert own.status_code == 200
    body = own.json()
    assert body["user"]["id"] == subj_id
    assert len(body["questionnaires"]) == 1
    assert "recalibration" in body

    intruder = _register_login(client, "exp_intr@example.com")
    forbidden = client.get(
        f"/export/employee/{subj_id}", headers={"Authorization": f"Bearer {intruder}"}
    )
    assert forbidden.status_code == 403


# --- pilot metric endpoint end-to-end ---


def test_pilot_metric_endpoint(client: TestClient):
    team_id = str(uuid.uuid4())
    hr = _register_login(client, "hr_pilot@example.com", role="hr")
    hr_headers = {"Authorization": f"Bearer {hr}"}

    # 3 members each: high baseline (5) then low day_90 (1) -> emergency drops 5->1.
    for n in range(3):
        tok = _register_login(client, f"pm{n}@example.com", team_id=team_id)
        uid = _me_id(client, tok)
        q_hi = _submit(client, tok, 5)
        _recal(client, tok, uid, "baseline", q_hi)
        q_lo = _submit(client, tok, 1)
        _recal(client, tok, uid, "day_90", q_lo)

    r = client.get(f"/compliance/pilot-metric/team/{team_id}", headers=hr_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["sufficient_data"] is True
    assert body["cohort_size"] == 3
    assert body["target_met"] is True
    assert body["headline"]["key"] == "emergency_pressure"
    assert body["headline"]["baseline_mean"] == 5.0
    assert body["headline"]["latest_mean"] == 1.0
    assert len(body["blocks"]) == 4

    # Plain employee cannot view pilot metrics.
    emp = _register_login(client, "pm_emp@example.com")
    assert (
        client.get(
            f"/compliance/pilot-metric/team/{team_id}",
            headers={"Authorization": f"Bearer {emp}"},
        ).status_code
        == 403
    )
