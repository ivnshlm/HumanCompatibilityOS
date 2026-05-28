"""Burnout & Environment Health scoring engine.

Spec formula (1–5 scale):
    Burnout Pressure = EmergencyPressure*0.30 + RecoveryDeficit*0.25
                     + CommunicationOverload*0.20 + InterruptionDensity*0.15
                     + LeadershipInstability*0.10
Risk thresholds: 0.0–1.9 Low · 2.0–3.4 Medium · 3.5–5.0 High.

The spec defines the 5 weighted components but not how the 15 questionnaire
items map onto them — that mapping is a product decision made here, grounded
in the question semantics and the example interpretation
(Q1/5/11 = burnout pressure, Q4/14 low = recovery risk, Q2/3 = communication/
interruption, Q9 low = psych safety, Q15 = environment chaos).

Each component score is the mean of its (orientation-adjusted) item values.
Items phrased positively (higher = healthier) are reverse-scored: 6 - value.
Explainability-first: compute_burnout_score returns the full per-component
breakdown, not just the final number.
"""

from dataclasses import dataclass
from enum import Enum

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


@dataclass(frozen=True)
class Question:
    index: int  # 1..15
    text: str
    component: Component
    # True when a higher raw answer means a *healthier* state and must be
    # reverse-scored (6 - value) before feeding the pressure formula.
    reverse: bool


# 15-item Burnout & Environment Health questionnaire (scale 1–5).
QUESTIONS: list[Question] = [
    Question(1, "Чувствуете ли вы операционное истощение после обычного рабочего дня?",
             Component.emergency_pressure, False),
    Question(2, "Мешают ли отвлечения удерживать устойчивую концентрацию?",
             Component.interruption_density, False),
    Question(3, "Ощущаются ли каналы коммуникации перегруженными или шумными?",
             Component.communication_overload, False),
    Question(4, "Полностью ли вы восстанавливаетесь между интенсивными периодами работы?",
             Component.recovery_deficit, True),
    Question(5, "Чувствуете ли вы давление работать в режиме постоянного аврала?",
             Component.emergency_pressure, False),
    Question(6, "Решения руководства скорее повышают напряжение? (выше — больше напряжения)",
             Component.leadership_instability, False),
    Question(7, "Испытываете ли вы когнитивную фрагментацию из-за многозадачности?",
             Component.interruption_density, False),
    Question(8, "Поддерживает ли ваша среда спокойную сосредоточенную работу?",
             Component.interruption_density, True),
    Question(9, "Чувствуете ли вы психологическую безопасность сообщать о перегрузке?",
             Component.leadership_instability, True),
    Question(10, "Остаются ли конфликты нерешёнными длительное время?",
             Component.leadership_instability, False),
    Question(11, "Чувствуете ли вы скрытое давление постоянно перевыполнять?",
             Component.emergency_pressure, False),
    Question(12, "Создаёт ли ваш текущий рабочий процесс дефицит восстановления?",
             Component.recovery_deficit, False),
    Question(13, "Встречи скорее изматывают, чем приносят пользу? (выше — больше изматывают)",
             Component.communication_overload, False),
    Question(14, "Считаете ли вы свой рабочий ритм устойчивым в долгосрочной перспективе?",
             Component.recovery_deficit, True),
    Question(15, "Ваша среда скорее повышает хаос, чем ясность? (выше — больше хаоса)",
             Component.leadership_instability, False),
]

QUESTION_INDICES: frozenset[int] = frozenset(q.index for q in QUESTIONS)

MIN_VALUE = 1
MAX_VALUE = 5


@dataclass(frozen=True)
class ComponentScore:
    component: Component
    label: str
    weight: float
    score: float  # mean of oriented item values, 1..5
    question_indices: list[int]


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


def _oriented_value(question: Question, raw: int) -> int:
    return (MAX_VALUE + MIN_VALUE) - raw if question.reverse else raw


def compute_burnout_score(answers: dict[int, int]) -> BurnoutResult:
    """Compute the weighted burnout-pressure score with a per-component breakdown.

    `answers` must contain every question index (1..15) with a value in 1..5.
    """
    missing = QUESTION_INDICES - answers.keys()
    if missing:
        raise ValueError(f"Missing answers for questions: {sorted(missing)}")
    for idx, value in answers.items():
        if idx not in QUESTION_INDICES:
            raise ValueError(f"Unknown question index: {idx}")
        if not (MIN_VALUE <= value <= MAX_VALUE):
            raise ValueError(f"Value for question {idx} out of range 1..5: {value}")

    grouped: dict[Component, list[int]] = {c: [] for c in Component}
    for question in QUESTIONS:
        grouped[question.component].append(_oriented_value(question, answers[question.index]))

    components: list[ComponentScore] = []
    total = 0.0
    for component in Component:
        values = grouped[component]
        mean = sum(values) / len(values)
        total += mean * COMPONENT_WEIGHTS[component]
        components.append(
            ComponentScore(
                component=component,
                label=COMPONENT_LABELS_RU[component],
                weight=COMPONENT_WEIGHTS[component],
                score=round(mean, 2),
                question_indices=[q.index for q in QUESTIONS if q.component == component],
            )
        )

    burnout_pressure = round(total, 2)
    return BurnoutResult(
        burnout_pressure=burnout_pressure,
        risk_level=risk_level_for(burnout_pressure),
        components=components,
    )
