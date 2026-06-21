"""Burnout & Environment Health scoring engine (Question Bank v0.1).

Spec formula (1-5 scale), unchanged from the original design:
    Burnout Pressure = EmergencyPressure*0.30 + RecoveryDeficit*0.25
                     + CommunicationOverload*0.20 + InterruptionDensity*0.15
                     + LeadershipInstability*0.10
Risk thresholds: 0.0-1.9 Low, 2.0-3.4 Medium, 3.5-5.0 High.

Items now come from the 75-question bank (app/question_bank.py) instead of a
hardcoded list. Scoring per item follows the bank's scoring_direction:
    pressure_direct   -> score = answer
    protective_reverse-> score = 6 - answer   (higher always = more pressure)
A component score is the item-weighted mean of its oriented item values; the
overall score is the component-weighted sum. So every component is oriented the
same way and downstream code (interpretation, dashboard, recalibration) is
unchanged — only the source of items and the keying (question_id) changed.
"""

from dataclasses import dataclass
from enum import Enum

from app import question_bank
from app.models import RiskLevel


class Component(str, Enum):
    emergency_pressure = "emergency_pressure"
    recovery_deficit = "recovery_deficit"
    communication_overload = "communication_overload"
    interruption_density = "interruption_density"
    leadership_instability = "leadership_instability"


COMPONENT_WEIGHTS: dict[Component, float] = {
    Component.emergency_pressure: 0.30,
    Component.recovery_deficit: 0.25,
    Component.communication_overload: 0.20,
    Component.interruption_density: 0.15,
    Component.leadership_instability: 0.10,
}

COMPONENT_LABELS_RU: dict[Component, str] = {
    Component.emergency_pressure: "Давление аврала",
    Component.recovery_deficit: "Дефицит восстановления",
    Component.communication_overload: "Коммуникационная перегрузка",
    Component.interruption_density: "Плотность отвлечений",
    Component.leadership_instability: "Нестабильность лидерства",
}

# Bank component_id (DA/DV/KP/PO/NL) -> internal Component enum.
COMPONENT_BY_BANK_ID: dict[str, Component] = {
    "DA": Component.emergency_pressure,
    "DV": Component.recovery_deficit,
    "KP": Component.communication_overload,
    "PO": Component.interruption_density,
    "NL": Component.leadership_instability,
}

MIN_VALUE = 1
MAX_VALUE = 5


@dataclass(frozen=True)
class ComponentScore:
    component: Component
    label: str
    weight: float
    score: float  # item-weighted mean of oriented item values, 1..5
    question_ids: list[str]


@dataclass(frozen=True)
class BurnoutResult:
    burnout_pressure: float  # 1..5, rounded to 2 decimals
    risk_level: RiskLevel
    components: list[ComponentScore]


def risk_level_for(score: float) -> RiskLevel:
    if score < 2.0:
        return RiskLevel.low
    if score < 3.5:
        return RiskLevel.medium
    return RiskLevel.high


def _oriented_value(scoring_direction: str, raw: int) -> int:
    """Orient an answer so higher always means more environment pressure."""
    if scoring_direction == "protective_reverse":
        return (MAX_VALUE + MIN_VALUE) - raw
    return raw


def compute_burnout_score(answers: dict[str, int]) -> BurnoutResult:
    """Compute the weighted burnout-pressure score with a per-component breakdown.

    `answers` maps bank question_id -> value (1..5). The set must cover all five
    components (every session level does) and reference only known questions.
    """
    if not answers:
        raise ValueError("No answers provided")

    grouped: dict[Component, list[tuple[float, float]]] = {c: [] for c in Component}  # (oriented, weight)
    grouped_ids: dict[Component, list[str]] = {c: [] for c in Component}

    for question_id, value in answers.items():
        question = question_bank.get(question_id)
        if question is None:
            raise ValueError(f"Unknown question_id: {question_id}")
        if not (MIN_VALUE <= value <= MAX_VALUE):
            raise ValueError(f"Value for {question_id} out of range 1..5: {value}")
        component = COMPONENT_BY_BANK_ID[question.component_id]
        oriented = _oriented_value(question.scoring_direction, value)
        grouped[component].append((oriented, question.item_weight))
        grouped_ids[component].append(question_id)

    missing = [c for c in Component if not grouped[c]]
    if missing:
        raise ValueError(f"No answers for components: {[c.value for c in missing]}")

    components: list[ComponentScore] = []
    total = 0.0
    for component in Component:
        pairs = grouped[component]
        weight_sum = sum(w for _, w in pairs)
        mean = sum(o * w for o, w in pairs) / weight_sum
        total += mean * COMPONENT_WEIGHTS[component]
        components.append(
            ComponentScore(
                component=component,
                label=COMPONENT_LABELS_RU[component],
                weight=COMPONENT_WEIGHTS[component],
                score=round(mean, 2),
                question_ids=sorted(grouped_ids[component]),
            )
        )

    burnout_pressure = round(total, 2)
    return BurnoutResult(
        burnout_pressure=burnout_pressure,
        risk_level=risk_level_for(burnout_pressure),
        components=components,
    )
