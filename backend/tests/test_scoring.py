import pytest

from app.models import RiskLevel
from app.scoring import (
    COMPONENT_WEIGHTS,
    QUESTION_INDICES,
    compute_burnout_score,
    risk_level_for,
)


def _all(value: int) -> dict[int, int]:
    return {i: value for i in QUESTION_INDICES}


def test_weights_sum_to_one():
    assert round(sum(COMPONENT_WEIGHTS.values()), 6) == 1.0


def test_fifteen_questions():
    assert QUESTION_INDICES == frozenset(range(1, 16))


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


def test_all_three_is_neutral_medium():
    result = compute_burnout_score(_all(3))
    assert result.burnout_pressure == 3.0
    assert result.risk_level == RiskLevel.medium
    assert len(result.components) == 5
    assert all(c.score == 3.0 for c in result.components)


def test_all_min_and_max():
    low = compute_burnout_score(_all(1))
    assert low.burnout_pressure == 1.97
    assert low.risk_level == RiskLevel.low

    high = compute_burnout_score(_all(5))
    assert high.burnout_pressure == 4.03
    assert high.risk_level == RiskLevel.high


def test_missing_answer_raises():
    answers = _all(3)
    answers.pop(7)
    with pytest.raises(ValueError, match="Missing answers"):
        compute_burnout_score(answers)


def test_out_of_range_raises():
    answers = _all(3)
    answers[5] = 9
    with pytest.raises(ValueError, match="out of range"):
        compute_burnout_score(answers)


def test_unknown_index_raises():
    answers = _all(3)
    answers[99] = 3
    with pytest.raises(ValueError, match="Unknown question index"):
        compute_burnout_score(answers)
