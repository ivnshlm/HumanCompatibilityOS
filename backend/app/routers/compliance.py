"""Compliance & pilot routes (Phase 6).

- GET /compliance/policy — the product's hard ethical constraints, machine-readable.
- GET /compliance/pilot-metric/team/{team_id} — pilot KPI: emergency-pressure
  change baseline → day 90 against the -20% target.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dashboard import BLOCK_LABELS_RU, DashboardBlock
from app.db import get_db
from app.deps import get_current_user
from app.models import Questionnaire, RecalibrationCycle, RecalibrationEvent, Role, User
from app.pilot import PILOT_TARGET_PCT, compute_pilot_report
from app.schemas import CompliancePolicyOut, MetricChangeOut, PilotMetricOut
from app.scoring import BurnoutResult, compute_burnout_score

# Human-readable labels for the pilot metric keys.
_METRIC_LABELS_RU: dict[str, str] = {
    "emergency_pressure": "Давление аврала",
    **{b.value: BLOCK_LABELS_RU[b] for b in DashboardBlock},
}

router = APIRouter(tags=["compliance"])

_REVIEWER_ROLES = {Role.hr, Role.team_lead, Role.admin, Role.ethics_reviewer}

_PRINCIPLES_RU = [
    "Explainability-first: каждый вывод объясним и проверяем.",
    "Никаких автоматических решений: индикаторы не являются основанием для кадровых действий.",
    "Обязательная проверка человеком для всех выводов.",
    "Явное согласие на сбор операционных данных и прозрачность.",
    "Аудит и анти-слежка: система не превращается в скрытый профайлинг.",
    "Оценивается операционная совместимость и устойчивость среды, а не ценность человека.",
]

_DISCLAIMER_RU = (
    "Светофор-индикаторы не являются основанием для кадровых решений. "
    "Все выводы требуют проверки человеком."
)


@router.get("/compliance/policy", response_model=CompliancePolicyOut)
def compliance_policy(user: User = Depends(get_current_user)) -> CompliancePolicyOut:
    return CompliancePolicyOut(
        principles=_PRINCIPLES_RU,
        no_automated_decisions=True,
        requires_consent=True,
        requires_human_review=True,
        pilot_metric="emergency_pressure_reduction_90d",
        pilot_target_pct=PILOT_TARGET_PCT,
        disclaimer=_DISCLAIMER_RU,
    )


def _result_for(db: Session, questionnaire_id: uuid.UUID | None) -> BurnoutResult | None:
    if questionnaire_id is None:
        return None
    questionnaire = db.get(Questionnaire, questionnaire_id)
    if questionnaire is None:
        return None
    answers = {a.question_id: a.value for a in questionnaire.answers}
    try:
        return compute_burnout_score(answers)
    except ValueError:
        return None


@router.get("/compliance/pilot-metric/team/{team_id}", response_model=PilotMetricOut)
def pilot_metric(
    team_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PilotMetricOut:
    if user.role not in _REVIEWER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient role to view pilot metrics",
        )
    if user.role == Role.team_lead and user.team_id != team_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Team leads may only view their own team",
        )

    members = db.scalars(select(User).where(User.team_id == team_id)).all()
    pairs: list[tuple[BurnoutResult, BurnoutResult]] = []
    for member in members:
        baseline_event = db.scalar(
            select(RecalibrationEvent)
            .where(
                RecalibrationEvent.user_id == member.id,
                RecalibrationEvent.cycle == RecalibrationCycle.baseline,
            )
            .order_by(RecalibrationEvent.created_at.asc())
            .limit(1)
        )
        day90_event = db.scalar(
            select(RecalibrationEvent)
            .where(
                RecalibrationEvent.user_id == member.id,
                RecalibrationEvent.cycle == RecalibrationCycle.day_90,
            )
            .order_by(RecalibrationEvent.created_at.desc())
            .limit(1)
        )
        if baseline_event is None or day90_event is None:
            continue
        base = _result_for(db, baseline_event.questionnaire_id)
        latest = _result_for(db, day90_event.questionnaire_id)
        if base is None or latest is None:
            continue
        pairs.append((base, latest))

    report = compute_pilot_report(pairs)

    def _out(mc) -> MetricChangeOut:
        return MetricChangeOut(
            key=mc.key,
            label=_METRIC_LABELS_RU.get(mc.key, mc.key),
            baseline_mean=mc.baseline_mean,
            latest_mean=mc.latest_mean,
            pct_change=mc.pct_change,
            improved=mc.improved,
        )

    return PilotMetricOut(
        team_id=team_id,
        cohort_size=report.cohort_size,
        sufficient_data=report.sufficient_data,
        target_pct=report.target_pct,
        target_met=report.target_met,
        headline=_out(report.headline) if report.headline else None,
        blocks=[_out(b) for b in report.blocks],
        notice=report.notice,
    )
