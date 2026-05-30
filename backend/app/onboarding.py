"""Onboarding stability: how well new hires integrate vs the settled team.

Spec calls for "onboarding stabilization" / lower "integration friction"
(Pilot_Metrics, System Scheme telemetry). Rather than a separate survey, we
derive it from the existing environment questionnaire: compare the burnout
pressure of recent hires (account created within the onboarding window) against
tenured colleagues. If new hires run materially hotter, that's integration
friction worth a human's attention.

Cross-sectional (new vs tenured), so it needs no per-user time series and no
schema change. Cohort-suppressed like the rest of the analytics.
"""

from dataclasses import dataclass
from statistics import mean

from app.dashboard import MIN_COHORT
from app.models import RiskLevel
from app.scoring import BurnoutResult

# A hire is "onboarding" while their account is younger than this.
ONBOARDING_WINDOW_DAYS = 90
# New-hire burnout pressure this far above tenured mean counts as friction.
FRICTION_THRESHOLD = 0.5


@dataclass(frozen=True)
class OnboardingHealth:
    cohort_size: int  # new hires with a scored questionnaire
    sufficient_data: bool
    new_hire_mean: float | None
    tenured_mean: float | None
    integration_friction: float | None  # new_hire_mean - tenured_mean
    friction_flag: bool
    at_risk_count: int  # new hires currently at high risk
    notice: str | None


def compute_onboarding_health(
    new_hire_results: list[BurnoutResult],
    tenured_results: list[BurnoutResult],
) -> OnboardingHealth:
    cohort_size = len(new_hire_results)
    if cohort_size < MIN_COHORT:
        return OnboardingHealth(
            cohort_size=cohort_size,
            sufficient_data=False,
            new_hire_mean=None,
            tenured_mean=None,
            integration_friction=None,
            friction_flag=False,
            at_risk_count=0,
            notice=(
                f"Недостаточно данных: нужно ≥ {MIN_COHORT} новых сотрудников "
                f"с заполненным опросником, сейчас {cohort_size}."
            ),
        )

    new_hire_mean = round(mean(r.burnout_pressure for r in new_hire_results), 2)
    at_risk = sum(1 for r in new_hire_results if r.risk_level == RiskLevel.high)

    if tenured_results:
        tenured_mean = round(mean(r.burnout_pressure for r in tenured_results), 2)
        friction = round(new_hire_mean - tenured_mean, 2)
        flag = friction > FRICTION_THRESHOLD
    else:
        tenured_mean = None
        friction = None
        flag = False

    return OnboardingHealth(
        cohort_size=cohort_size,
        sufficient_data=True,
        new_hire_mean=new_hire_mean,
        tenured_mean=tenured_mean,
        integration_friction=friction,
        friction_flag=flag,
        at_risk_count=at_risk,
        notice=None,
    )
