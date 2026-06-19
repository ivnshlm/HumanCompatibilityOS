"""Tests for the interpretation layer (app/interpretation.py).

The generator is a pure function of component scores, so the reference examples
A and B from "Интерпретация результата для Архитектора · v0.1" are fed as
component scores directly — decoupled from the 15-question mapping.
"""

import pytest

from app.interpretation import (
    FORBIDDEN_PHRASES,
    build_interpretation,
)
from app.models import RiskLevel
from app.scoring import (
    COMPONENT_LABELS_RU,
    COMPONENT_WEIGHTS,
    BurnoutResult,
    Component,
    ComponentScore,
    risk_level_for,
)


def _result(total: float, **scores: float) -> BurnoutResult:
    """Build a BurnoutResult straight from component scores (1..5)."""
    components = [
        ComponentScore(
            component=c,
            label=COMPONENT_LABELS_RU[c],
            weight=COMPONENT_WEIGHTS[c],
            score=scores[c.value],
            question_indices=[],
        )
        for c in Component
    ]
    return BurnoutResult(
        burnout_pressure=total,
        risk_level=risk_level_for(total),
        components=components,
    )


# Reference example A: 2.77 / medium — aval + interruptions dominate, recovery
# is a close 3rd, leadership stable.
EXAMPLE_A = _result(
    2.77,
    emergency_pressure=3.33,
    recovery_deficit=3.00,
    communication_overload=2.00,
    interruption_density=3.33,
    leadership_instability=1.25,
)

# Reference example B: 2.20 / medium — aval + communication dominate, recovery
# and leadership stable.
EXAMPLE_B = _result(
    2.20,
    emergency_pressure=3.00,
    recovery_deficit=1.00,
    communication_overload=3.00,
    interruption_density=2.33,
    leadership_instability=1.00,
)


def _all_text(interp) -> str:
    parts = [interp.summary, interp.possible_meaning, interp.disclaimer]
    parts += interp.check_next
    parts += [f.title + " " + f.explanation for f in interp.dominant_factors]
    return " ".join(parts).lower()


def test_example_a_dominant_factors():
    interp = build_interpretation(EXAMPLE_A)
    keys = [f.key for f in interp.dominant_factors]
    # Top two are the tied 3.33 factors; recovery (3.00) is a close 3rd.
    assert keys[:2] == ["emergency_pressure", "interruption_density"]
    assert "recovery_deficit" in keys
    assert len(keys) == 3
    # Stable leadership → summary reassures it is likely not a management issue.
    assert "лидерский контур" in interp.summary.lower()
    assert "среднего риска перегруза" in interp.summary.lower()


def test_example_b_dominant_factors():
    interp = build_interpretation(EXAMPLE_B)
    keys = [f.key for f in interp.dominant_factors]
    # Only two drivers; interruption (2.33) is below the 3rd-factor floor.
    assert keys == ["emergency_pressure", "communication_overload"]
    assert len(keys) == 2


def test_check_next_count_within_bounds():
    for example in (EXAMPLE_A, EXAMPLE_B):
        interp = build_interpretation(example)
        assert 3 <= len(interp.check_next) <= 5
        assert len(interp.check_next) == len(set(interp.check_next))  # deduped


def test_disclaimer_present_and_non_decisional():
    interp = build_interpretation(EXAMPLE_A)
    assert "не является" in interp.disclaimer
    assert "кадрового решения" in interp.disclaimer


@pytest.mark.parametrize("example", [EXAMPLE_A, EXAMPLE_B])
def test_no_forbidden_phrases(example):
    text = _all_text(build_interpretation(example))
    for phrase in FORBIDDEN_PHRASES:
        assert phrase not in text, f"forbidden phrase leaked: {phrase!r}"


def test_high_leadership_is_named_as_contour_not_person():
    # Leadership is the dominant driver — must read as "contour", never blame
    # the manager (forbidden: "руководитель нестабилен").
    result = _result(
        3.6,
        emergency_pressure=2.00,
        recovery_deficit=2.00,
        communication_overload=2.00,
        interruption_density=2.00,
        leadership_instability=4.50,
    )
    interp = build_interpretation(result)
    text = _all_text(interp)
    assert interp.dominant_factors[0].key == "leadership_instability"
    assert "лидерск" in text
    assert "руководитель нестабилен" not in text
    # No "stable leadership" reassurance when leadership is actually the driver.
    assert "выглядит относительно стабильным" not in interp.summary.lower()


def test_low_risk_is_calm_not_all_clear():
    result = _result(
        1.5,
        emergency_pressure=1.5,
        recovery_deficit=1.5,
        communication_overload=1.5,
        interruption_density=1.5,
        leadership_instability=1.5,
    )
    assert risk_level_for(1.5) == RiskLevel.low
    interp = build_interpretation(result)
    text = interp.summary.lower()
    # Tone rule §6: low risk must not read as "no risk" / "fine forever".
    assert "рисков нет" not in text
    assert "всё хорошо навсегда" not in text
