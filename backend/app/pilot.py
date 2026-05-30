"""Pilot success metric: emergency-pressure reduction over the cycle.

Pilot target from the spec: a >= 20% drop in emergency pressure within 90 days.
We compare each member's emergency-pressure component at the baseline cycle
against the day-90 cycle, aggregate across the team, and report whether the
target is met. Cohort-suppressed like the dashboard (anti-surveillance).
"""

from dataclasses import dataclass
from statistics import mean

from app.dashboard import MIN_COHORT
from app.scoring import BurnoutResult, Component

# Target: emergency pressure should fall by at least this percentage.
PILOT_TARGET_PCT = -20.0


def emergency_pressure(result: BurnoutResult) -> float:
    """Extract the emergency-pressure component score from a scored result."""
    for component in result.components:
        if component.component == Component.emergency_pressure:
            return component.score
    raise ValueError("emergency_pressure component missing from result")


@dataclass(frozen=True)
class PilotMetric:
    cohort_size: int
    sufficient_data: bool
    baseline_mean: float | None
    latest_mean: float | None
    pct_change: float | None
    target_pct: float
    target_met: bool
    notice: str | None


def compute_pilot_metric(pairs: list[tuple[float, float]]) -> PilotMetric:
    """Aggregate (baseline, day_90) emergency-pressure pairs into the pilot KPI.

    Only members with BOTH a baseline and a day-90 point contribute.
    """
    cohort_size = len(pairs)
    if cohort_size < MIN_COHORT:
        return PilotMetric(
            cohort_size=cohort_size,
            sufficient_data=False,
            baseline_mean=None,
            latest_mean=None,
            pct_change=None,
            target_pct=PILOT_TARGET_PCT,
            target_met=False,
            notice=(
                f"Недостаточно данных: нужно ≥ {MIN_COHORT} участников с точками "
                f"baseline и 90 дней, сейчас {cohort_size}."
            ),
        )

    baseline_mean = round(mean(b for b, _ in pairs), 2)
    latest_mean = round(mean(d for _, d in pairs), 2)
    pct_change = (
        round((latest_mean - baseline_mean) / baseline_mean * 100, 1)
        if baseline_mean != 0
        else 0.0
    )
    return PilotMetric(
        cohort_size=cohort_size,
        sufficient_data=True,
        baseline_mean=baseline_mean,
        latest_mean=latest_mean,
        pct_change=pct_change,
        target_pct=PILOT_TARGET_PCT,
        target_met=pct_change <= PILOT_TARGET_PCT,
        notice=None,
    )
