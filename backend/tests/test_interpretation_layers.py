"""PR3 enrichment: subdimension + drill-down follow-ups + role report layers."""

from app.interpretation import FORBIDDEN_PHRASES, build_interpretation, build_report_layer
from app.scoring import compute_burnout_score

from conftest import bank_scores


def _result_and_answers(value: int = 4):
    answers = bank_scores(value)
    return compute_burnout_score(answers), answers


def test_followups_and_subdimension_from_answers():
    result, answers = _result_and_answers()
    interp = build_interpretation(result, answers)
    assert interp.follow_ups, "drill-down follow-up questions should be surfaced"
    assert all(f.subdimension for f in interp.dominant_factors)


def test_no_enrichment_without_answers():
    result, _ = _result_and_answers()
    interp = build_interpretation(result)  # legacy / no answers
    assert interp.follow_ups is None
    assert all(f.subdimension == "" for f in interp.dominant_factors)


def test_report_layer_by_role():
    result, _ = _result_and_answers()
    # The subject (participant) gets no extra layer — just the base reading.
    assert build_report_layer(result, "employee") is None

    hrd = build_report_layer(result, "hr")
    assert hrd is not None and hrd.layer == "hrd" and hrd.notes
    assert hrd.description

    assert build_report_layer(result, "team_lead").layer == "manager"
    assert build_report_layer(result, "admin").layer == "architect"
    assert build_report_layer(result, "ethics_reviewer").layer == "architect"


def test_report_layer_has_no_forbidden_phrases():
    result, _ = _result_and_answers()
    for role in ("hr", "team_lead", "admin", "ethics_reviewer"):
        layer = build_report_layer(result, role)
        text = (layer.description + " " + " ".join(n.note for n in layer.notes)).lower()
        for phrase in FORBIDDEN_PHRASES:
            assert phrase not in text, f"forbidden phrase in {role} layer: {phrase!r}"
