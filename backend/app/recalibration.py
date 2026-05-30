"""Recalibration engine: trend vs baseline + development recommendations.

Cycle: baseline → 30 days → 90 days → retrospective. Each recalibration event
anchors to a scored questionnaire; the engine compares a later cycle's burnout
pressure against the baseline and derives **advisory** development suggestions
from the dominant pressure component.

Doctrine: recommendations are environment/development suggestions for human
review — never an automated personnel action. Explainability-first: every
recommendation traces back to the named component that triggered it.
"""

from enum import Enum

from app.scoring import BurnoutResult, Component

# Minimum change in burnout pressure (1–5 scale) to call a trend, not noise.
TREND_THRESHOLD = 0.3

# A component is a "driver" worth a recommendation at/above this score.
DRIVER_THRESHOLD = 3.5


class Trend(str, Enum):
    improving = "improving"  # burnout pressure dropped vs baseline
    worsening = "worsening"
    stable = "stable"
    insufficient = "insufficient"  # no baseline / no later point to compare


TREND_LABELS_RU: dict[Trend, str] = {
    Trend.improving: "Улучшение относительно базовой точки",
    Trend.worsening: "Ухудшение относительно базовой точки",
    Trend.stable: "Без значимых изменений",
    Trend.insufficient: "Недостаточно данных для сравнения",
}

# Advisory development recommendations keyed by the dominant pressure driver.
RECOMMENDATIONS_RU: dict[Component, str] = {
    Component.emergency_pressure: (
        "Снизить долю авральных задач: ввести буферы в планировании и явные критерии "
        "«это действительно срочно»."
    ),
    Component.recovery_deficit: (
        "Защитить время восстановления: реальные паузы, разгрузка пиков, отказ от работы "
        "в нерабочее время."
    ),
    Component.communication_overload: (
        "Сократить коммуникационный шум: меньше параллельных каналов и встреч, перейти на "
        "асинхронные дайджесты."
    ),
    Component.interruption_density: (
        "Ввести блоки фокус-времени и защиту от прерываний; группировать переключения "
        "контекста."
    ),
    Component.leadership_instability: (
        "Прояснить приоритеты со стороны руководства: регулярные 1:1, своевременный разбор "
        "конфликтов, предсказуемость решений."
    ),
}

_NO_DRIVER_RU = "Показатели в пределах нормы — поддерживайте текущие практики среды."


def trend_for(baseline: float | None, latest: float | None) -> Trend:
    """Trend of burnout pressure: lower is better, so a drop == improving."""
    if baseline is None or latest is None:
        return Trend.insufficient
    delta = round(latest - baseline, 2)
    if delta <= -TREND_THRESHOLD:
        return Trend.improving
    if delta >= TREND_THRESHOLD:
        return Trend.worsening
    return Trend.stable


def recommendations_for(result: BurnoutResult, threshold: float = DRIVER_THRESHOLD) -> list[str]:
    """Advisory suggestions for each high-pressure component, strongest first."""
    drivers = sorted(
        (c for c in result.components if c.score >= threshold),
        key=lambda c: c.score,
        reverse=True,
    )
    if not drivers:
        return [_NO_DRIVER_RU]
    return [RECOMMENDATIONS_RU[c.component] for c in drivers]
