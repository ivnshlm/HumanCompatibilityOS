import pytest

from app import question_bank
from app.models import RiskLevel
from app.scoring import (
    COMPONENT_BY_BANK_ID,
    COMPONENT_WEIGHTS,
    compute_burnout_score,
    risk_level_for,
)


def _all(value: int, level: str = "short") -> dict[str, int]:
    return {qid: value for qid in question_bank.select_session(level)}


def test_bank_integrity():
    question_bank.validate_bank()
    assert len(question_bank.select_session("short")) == 15
    assert len(question_bank.select_session("base")) == 25
    assert len(question_bank.select_session("deep")) == 40


def test_weights_sum_to_one():
    assert round(sum(COMPONENT_WEIGHTS.values()), 6) == 1.0


def test_component_mapping_covers_all_bank_components():
    assert set(COMPONENT_BY_BANK_ID) == set(question_bank.COMPONENT_ORDER)


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.0, RiskLevel.low),
        (1.9, RiskLevel.low),
        (2.0, RiskLevel.medium),
        (3.4, RiskLevel.medium),
        (3.5, RiskLevel.high),
        (5.0, RiskLevel.high),
    ],
)
def test_risk_thresholds(score, expected):
    assert risk_level_for(score) == expected


@pytest.mark.parametrize("level", ["short", "base", "deep"])
def test_all_three_is_neutral_medium(level):
    # Neutral answer (3) is invariant under reverse-scoring (6-3 == 3),
    # so every component and the overall score is exactly 3.0 at any level.
    result = compute_burnout_score(_all(3, level))
    assert result.burnout_pressure == 3.0
    assert result.risk_level == RiskLevel.medium
    assert len(result.components) == 5
    assert all(c.score == 3.0 for c in result.components)


def test_min_is_low_max_is_high():
    low = compute_burnout_score(_all(1))
    assert low.risk_level == RiskLevel.low
    assert low.burnout_pressure < 2.0

    high = compute_burnout_score(_all(5))
    assert high.risk_level == RiskLevel.high
    assert high.burnout_pressure >= 3.5


def test_reverse_scoring_orientation():
    # On a protective (reverse) item a HIGHER answer means LESS pressure
    # (6 - answer). Flipping one reverse item from neutral 3 to 5 must lower its
    # component score below 3.0, while a direct item raises it.
    short = question_bank.select_session("short")
    rev_id = next(q for q in short if question_bank.get(q).scoring_direction == "protective_reverse")
    rev_comp = COMPONENT_BY_BANK_ID[question_bank.get(rev_id).component_id]

    answers = _all(3)
    answers[rev_id] = 5
    score = next(c.score for c in compute_burnout_score(answers).components if c.component == rev_comp)
    assert score < 3.0

    answers[rev_id] = 1
    score = next(c.score for c in compute_burnout_score(answers).components if c.component == rev_comp)
    assert score > 3.0


def test_missing_component_raises():
    answers = _all(3)
    # Drop a whole component -> cannot compute overall.
    answers = {qid: v for qid, v in answers.items() if not qid.startswith("HCO_DA_")}
    with pytest.raises(ValueError, match="No answers for components"):
        compute_burnout_score(answers)


def test_out_of_range_raises():
    answers = _all(3)
    first = next(iter(answers))
    answers[first] = 9
    with pytest.raises(ValueError, match="out of range"):
        compute_burnout_score(answers)


def test_unknown_question_id_raises():
    answers = _all(3)
    answers["HCO_XX_999"] = 3
    with pytest.raises(ValueError, match="Unknown question_id"):
        compute_burnout_score(answers)
