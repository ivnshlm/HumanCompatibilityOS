"""Dashboard aggregation: team-level environment-health blocks & metric rollups.

The dashboard never exposes an individual's score. It rolls up the *latest*
questionnaire of each team member into four environment-health blocks, derived
deterministically from the five scoring components (so the view stays
explainable — every block traces back to named components).

Blocks (all on the 1–5 "concern" scale, higher = more risk):
    burnout_pressure        — overall weighted Burnout Pressure
    recovery_sustainability — recovery_deficit (higher = less sustainable)
    communication_entropy   — mean(communication_overload, interruption_density)
    leadership_stability    — leadership_instability (higher = less stable)

Anti-surveillance doctrine: aggregates are suppressed below MIN_COHORT
contributors, so a "team dashboard" can never become a single-person profile.
"""

from dataclasses import dataclass
from enum import Enum
from statistics import mean

from app.models import RiskLevel
from app.scoring import BurnoutResult, Component, risk_level_for


class DashboardBlock(str, Enum):
    burnout_pressure = "burnout_pressure"
    recovery_sustainability = "recovery_sustainability"
    communication_entropy = "communication_entropy"
    leadership_stability = "leadership_stability"


BLOCK_LABELS_RU: dict[DashboardBlock, str] = {
    # Safe language: name the environment pressure, not a medical "выгорание".
    DashboardBlock.burnout_pressure: "Давление среды",
    DashboardBlock.recovery_sustainability: "Устойчивость восстановления",
    DashboardBlock.communication_entropy: "Коммуникационная энтропия",
    DashboardBlock.leadership_stability: "Устойчивость лидерства",
}

BLOCK_LABELS_EN: dict[DashboardBlock, str] = {
    DashboardBlock.burnout_pressure: "Burnout Pressure",
    DashboardBlock.recovery_sustainability: "Recovery Sustainability",
    DashboardBlock.communication_entropy: "Communication Entropy",
    DashboardBlock.leadership_stability: "Leadership Stability",
}

# Minimum number of contributing members before any aggregate is exposed.
# Below this, the dashboard reports "insufficient data" instead of numbers —
# small cohorts would de-anonymize individuals.
MIN_COHORT = 3

# Every block reads as "higher = more concern", consistent with the risk scale.
INTERPRETATION_RU = "Выше — больше риска. Это среда-агрегаты, не основание для кадровых решений."


@dataclass(frozen=True)
class BlockAggregate:
    block: DashboardBlock
    label: str
    label_en: str
    score: float  # mean across the cohort, 1..5
    risk_level: RiskLevel
    distribution: dict[str, int]  # member counts per risk band: low / medium / high


@dataclass(frozen=True)
class TeamDashboard:
    cohort_size: int
    sufficient_data: bool
    blocks: list[BlockAggregate]
    notice: str | None


def member_block_values(result: BurnoutResult) -> dict[DashboardBlock, float]:
    """Map one member's scored result onto the four dashboard blocks."""
    comp = {c.component: c.score for c in result.components}
    return {
        DashboardBlock.burnout_pressure: result.burnout_pressure,
        DashboardBlock.recovery_sustainability: comp[Component.recovery_deficit],
        DashboardBlock.communication_entropy: round(
            (comp[Component.communication_overload] + comp[Component.interruption_density]) / 2, 2
        ),
        DashboardBlock.leadership_stability: comp[Component.leadership_instability],
    }


def aggregate_team(results: list[BurnoutResult]) -> TeamDashboard:
    """Roll up members' latest results into the four blocks (cohort-suppressed)."""
    cohort_size = len(results)
    if cohort_size < MIN_COHORT:
        return TeamDashboard(
            cohort_size=cohort_size,
            sufficient_data=False,
            blocks=[],
            notice=(
                "Недостаточно данных для командного вывода. Чтобы защитить участников "
                f"от деанонимизации, командная аналитика доступна только при выборке "
                f"от {MIN_COHORT} человек (сейчас {cohort_size})."
            ),
        )

    per_member = [member_block_values(r) for r in results]
    blocks: list[BlockAggregate] = []
    for block in DashboardBlock:
        values = [m[block] for m in per_member]
        block_mean = round(mean(values), 2)
        distribution = {"low": 0, "medium": 0, "high": 0}
        for value in values:
            distribution[risk_level_for(value).value] += 1
        blocks.append(
            BlockAggregate(
                block=block,
                label=BLOCK_LABELS_RU[block],
                label_en=BLOCK_LABELS_EN[block],
                score=block_mean,
                risk_level=risk_level_for(block_mean),
                distribution=distribution,
            )
        )

    return TeamDashboard(cohort_size=cohort_size, sufficient_data=True, blocks=blocks, notice=None)


@dataclass(frozen=True)
class MetricAggregate:
    metric_type: str
    count: int
    mean: float
    minimum: float
    maximum: float


def aggregate_metrics(rows: list) -> list[MetricAggregate]:
    """Group environment-metric rows by type into count/mean/min/max rollups.

    `rows` are duck-typed objects exposing `.metric_type` and `.value`. Raw
    per-row values are never returned — only rollups (anti-surveillance).
    Trend/"latest" reporting is deferred to the recalibration phase, where a
    proper time axis exists.
    """
    by_type: dict[str, list[float]] = {}
    for row in rows:
        by_type.setdefault(row.metric_type, []).append(row.value)

    aggregates: list[MetricAggregate] = []
    for metric_type, values in sorted(by_type.items()):
        aggregates.append(
            MetricAggregate(
                metric_type=metric_type,
                count=len(values),
                mean=round(sum(values) / len(values), 2),
                minimum=min(values),
                maximum=max(values),
            )
        )
    return aggregates
