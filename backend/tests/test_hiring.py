from fastapi.testclient import TestClient

from app.hiring import suggest_overall_risk
from app.models import OverallRisk


def _register_login(client: TestClient, email: str, role: str = "employee") -> str:
    client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "full_name": f"U {email}", "role": role},
    )
    return client.post(
        "/auth/login", json={"email": email, "password": "password123"}
    ).json()["access_token"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# --- Unit: advisory suggestion ---


def test_suggest_overall_risk():
    assert suggest_overall_risk({"a": "low", "b": "low"}) == OverallRisk.green
    assert suggest_overall_risk({"a": "high", "b": "low"}) == OverallRisk.yellow
    assert suggest_overall_risk({"a": "medium", "b": "medium"}) == OverallRisk.yellow
    assert suggest_overall_risk({"a": "high", "b": "high"}) == OverallRisk.red


# --- reference ---


def test_reference_requires_role(client: TestClient):
    emp = _register_login(client, "emp_h@example.com")
    assert client.get("/hiring/reference", headers=_h(emp)).status_code == 403

    hr = _register_login(client, "hr_ref@example.com", role="hr")
    r = client.get("/hiring/reference", headers=_h(hr))
    assert r.status_code == 200
    body = r.json()
    assert len(body["signals"]) == 10
    assert body["quick_screen_signals"] == [
        "explainability",
        "feedback_stability",
        "chaos_relationship",
        "responsibility",
    ]
    assert len(body["decision_guidance"]) >= 3


# --- candidate + assessment + development plan flow ---


def test_candidate_assessment_flow(client: TestClient):
    hr = _register_login(client, "hr_hire@example.com", role="hr")

    # Employee cannot create candidates.
    emp = _register_login(client, "emp_hire@example.com")
    assert (
        client.post("/hiring/candidates", json={"full_name": "X"}, headers=_h(emp)).status_code
        == 403
    )

    cand = client.post(
        "/hiring/candidates",
        json={"full_name": "John D.", "role": "Sales Lead"},
        headers=_h(hr),
    )
    assert cand.status_code == 201
    cid = cand.json()["id"]

    # Quick screen assessment with 4 signals.
    a = client.post(
        f"/hiring/candidates/{cid}/assessments",
        json={
            "type": "quick_screen",
            "signals": {
                "explainability": "medium",
                "feedback_stability": "low",
                "chaos_relationship": "high",
                "responsibility": "medium",
            },
            "overall_risk": "yellow",
            "recommendation": "Conditional",
            "source_of_evidence": "Interview",
        },
        headers=_h(hr),
    )
    assert a.status_code == 201
    body = a.json()
    assert body["type"] == "quick_screen"
    assert body["overall_risk"] == "yellow"
    # 1 high -> suggested yellow (advisory).
    assert body["suggested_overall_risk"] == "yellow"
    assert body["reviewer_name"] == "U hr_hire@example.com"

    # Development plan.
    dp = client.post(
        f"/hiring/candidates/{cid}/development-plan",
        json={"risk_area": "Chaos Relationship", "suggested_support": "Pilot + supervision"},
        headers=_h(hr),
    )
    assert dp.status_code == 201

    # Detail aggregates everything.
    detail = client.get(f"/hiring/candidates/{cid}", headers=_h(hr)).json()
    assert detail["candidate"]["full_name"] == "John D."
    assert len(detail["assessments"]) == 1
    assert len(detail["development_plans"]) == 1


def test_list_candidates_forbidden_for_employee(client: TestClient):
    emp = _register_login(client, "emp_list@example.com")
    assert client.get("/hiring/candidates", headers=_h(emp)).status_code == 403
