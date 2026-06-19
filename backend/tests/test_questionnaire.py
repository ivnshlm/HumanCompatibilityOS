import uuid

from fastapi.testclient import TestClient

from conftest import promote_role


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


def _answers(value: int = 3) -> list[dict]:
    return [{"question_index": i, "value": value} for i in range(1, 16)]


def test_list_questions(client: TestClient):
    r = client.get("/questionnaire/questions")
    assert r.status_code == 200
    questions = r.json()
    assert len(questions) == 15
    assert {q["index"] for q in questions} == set(range(1, 16))


def test_submit_requires_consent(client: TestClient):
    token = _register_login(client, "noconsent@example.com", consent=False)
    r = client.post(
        "/questionnaire/submit",
        json={"answers": _answers(3)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


def test_submit_and_score(client: TestClient):
    token = _register_login(client, "submit@example.com")
    r = client.post(
        "/questionnaire/submit",
        json={"answers": _answers(3)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["burnout_pressure_score"] == 3.0
    assert body["risk_level"] == "medium"
    assert len(body["components"]) == 5
    assert body["interpretation"]["summary"]
    assert body["interpretation"]["disclaimer"]


def test_submit_incomplete_rejected(client: TestClient):
    token = _register_login(client, "incomplete@example.com")
    r = client.post(
        "/questionnaire/submit",
        json={"answers": _answers(3)[:14]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400


def test_submit_out_of_range_rejected_by_schema(client: TestClient):
    token = _register_login(client, "range@example.com")
    bad = _answers(3)
    bad[0]["value"] = 9
    r = client.post(
        "/questionnaire/submit",
        json={"answers": bad},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


def test_history_own(client: TestClient):
    token = _register_login(client, "hist@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/auth/me", headers=headers).json()
    client.post("/questionnaire/submit", json={"answers": _answers(4)}, headers=headers)

    r = client.get(f"/employee/{me['id']}/history", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_history_rbac(client: TestClient):
    emp_token = _register_login(client, "subject@example.com")
    emp_headers = {"Authorization": f"Bearer {emp_token}"}
    subject_id = client.get("/auth/me", headers=emp_headers).json()["id"]
    client.post("/questionnaire/submit", json={"answers": _answers(2)}, headers=emp_headers)

    # Another plain employee cannot view the subject's history.
    other_token = _register_login(client, "other@example.com")
    r = client.get(
        f"/employee/{subject_id}/history",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert r.status_code == 403

    # An HR reviewer can.
    hr_token = _register_login(client, "hr@example.com", role="hr")
    r = client.get(
        f"/employee/{subject_id}/history",
        headers={"Authorization": f"Bearer {hr_token}"},
    )
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_detail_own_has_interpretation(client: TestClient):
    token = _register_login(client, "detail_own@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    qid = client.post(
        "/questionnaire/submit", json={"answers": _answers(4)}, headers=headers
    ).json()["id"]

    r = client.get(f"/questionnaire/{qid}", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == qid
    assert len(body["components"]) == 5
    assert body["interpretation"]["summary"]
    assert body["interpretation"]["dominant_factors"]
    assert body["interpretation"]["check_next"]


def test_detail_rbac_and_404(client: TestClient):
    emp_token = _register_login(client, "detail_subj@example.com")
    emp_headers = {"Authorization": f"Bearer {emp_token}"}
    qid = client.post(
        "/questionnaire/submit", json={"answers": _answers(2)}, headers=emp_headers
    ).json()["id"]

    # Another plain employee cannot view someone else's individual result.
    other = _register_login(client, "detail_other@example.com")
    r = client.get(f"/questionnaire/{qid}", headers={"Authorization": f"Bearer {other}"})
    assert r.status_code == 403

    # A reviewer can.
    hr = _register_login(client, "detail_hr@example.com", role="hr")
    r = client.get(f"/questionnaire/{qid}", headers={"Authorization": f"Bearer {hr}"})
    assert r.status_code == 200

    # Unknown id → 404.
    r = client.get(f"/questionnaire/{uuid.uuid4()}", headers=emp_headers)
    assert r.status_code == 404
