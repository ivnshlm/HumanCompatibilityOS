"""Pilot success metrics: emergency-pressure target + full environment trends.

Spec pilot metrics (Pilot_Metrics / Technical Spec v2):
  - Burnout Pressure: reduce average emergency-mode pressure by >= 20% in 90 days.
  - Recovery Sustainability: improve (recovery deficit goes down).
  - Communication Entropy: reduce overload/noise.
  - Leadership Stability: reduce overload escalation.

All four dashboard blocks live on the 1-5 "concern" scale (higher = worse), so
"improvement" is a *decrease* for every block. We compare each member's value at
the baseline cycle against the day-90 cycle, aggregate across the team, and
report the percentage change. Cohort-suppressed like the dashboard.
"""

from dataclasses import dataclass
from statistics import mean

from app.dashboard import MIN_COHORT, DashboardBlock, member_block_values
from app.scoring import BurnoutResult, Component

# Headline pilot target: emergency pressure should fall by at least this percent.
PILOT_TARGET_PCT = -20.0


def emergency_pressure(result: BurnoutResult) -> float:
    """Emergency-pressure component score from a scored result."""
    for component in result.components:
        if component.component == Component.emergency_pressure:
            return component.score
    raise ValueError("emergency_pressure component missing from result")


@dataclass(frozen=True)
class MetricChange:
    key: str
    baseline_mean: float
    latest_mean: float
    pct_change: float  # negative = improvement (concern went down)
    improved: bool


@dataclass(frozen=True)
class PilotReport:
    cohort_size: int
    sufficient_data: bool
    target_pct: float
    target_met: bool  # headline: emergency pressure dropped >= 20%
    headline: MetricChange | None
    blocks: list[MetricChange]
    notice: str | None


def _change(key: str, pairs: list[tuple[float, float]]) -> MetricChange:
    baseline_mean = round(mean(b for b, _ in pairs), 2)
    latest_mean = round(mean(d for _, d in pairs), 2)
    pct = (
        round((latest_mean - baseline_mean) / baseline_mean * 100, 1)
        if baseline_mean != 0
        else 0.0
    )
    return MetricChange(
        key=key,
        baseline_mean=baseline_mean,
        latest_mean=latest_mean,
        pct_change=pct,
        improved=pct < 0,
    )


def compute_pilot_report(pairs: list[tuple[BurnoutResult, BurnoutResult]]) -> PilotReport:
    """Build the pilot report from per-member (baseline, day_90) scored results.

    Only members with BOTH a baseline and a day-90 result contribute.
    """
    cohort_size = len(pairs)
    if cohort_size < MIN_COHORT:
        return PilotReport(
            cohort_size=cohort_size,
            sufficient_data=False,
            target_pct=PILOT_TARGET_PCT,
            target_met=False,
            headline=None,
            blocks=[],
            notice=(
                f"Недостаточно данных: нужно ≥ {MIN_COHORT} участников с точками "
                f"baseline и 90 дней, сейчас {cohort_size}."
            ),
        )

    # Headline — emergency pressure.
    emergency_pairs = [(emergency_pressure(b), emergency_pressure(d)) for b, d in pairs]
    headline = _change("emergency_pressure", emergency_pairs)

    # Per-block environment trends (all four dashboard blocks).
    blocks: list[MetricChange] = []
    for block in DashboardBlock:
        block_pairs = [
            (member_block_values(b)[block], member_block_values(d)[block]) for b, d in pairs
        ]
        blocks.append(_change(block.value, block_pairs))

    return PilotReport(
        cohort_size=cohort_size,
        sufficient_data=True,
        target_pct=PILOT_TARGET_PCT,
        target_met=headline.pct_change <= PILOT_TARGET_PCT,
        headline=headline,
        blocks=blocks,
        notice=None,
    )
