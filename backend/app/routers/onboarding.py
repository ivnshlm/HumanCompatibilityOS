"""Onboarding stability route (Phase 8).

GET /onboarding/team/{team_id} — compares recent hires' environment health
against tenured colleagues to surface integration friction. Reviewer-only,
team-lead scoped, cohort-suppressed.
"""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Questionnaire, Role, User
from app.onboarding import ONBOARDING_WINDOW_DAYS, compute_onboarding_health
from app.schemas import OnboardingHealthOut
from app.scoring import BurnoutResult, compute_burnout_score

router = APIRouter(tags=["onboarding"])

_REVIEWER_ROLES = {Role.hr, Role.team_lead, Role.admin, Role.ethics_reviewer}


def _latest_result(db: Session, user_id: uuid.UUID) -> BurnoutResult | None:
    questionnaire = db.scalar(
        select(Questionnaire)
        .where(
            Questionnaire.user_id == user_id,
            Questionnaire.burnout_pressure_score.is_not(None),
        )
        .order_by(Questionnaire.submitted_at.desc())
        .limit(1)
    )
    if questionnaire is None:
        return None
    answers = {a.question_id: a.value for a in questionnaire.answers}
    try:
        return compute_burnout_score(answers)
    except ValueError:
        return None


@router.get("/onboarding/team/{team_id}", response_model=OnboardingHealthOut)
def onboarding_health(
    team_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnboardingHealthOut:
    if user.role not in _REVIEWER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient role to view onboarding health",
        )
    if user.role == Role.team_lead and user.team_id != team_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Team leads may only view their own team",
        )

    cutoff = datetime.now(UTC) - timedelta(days=ONBOARDING_WINDOW_DAYS)
    members = db.scalars(select(User).where(User.team_id == team_id)).all()

    new_hire_results: list[BurnoutResult] = []
    tenured_results: list[BurnoutResult] = []
    for member in members:
        result = _latest_result(db, member.id)
        if result is None:
            continue
        # created_at may be naive (SQLite); compare on UTC-aware terms.
        created = member.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        if created >= cutoff:
            new_hire_results.append(result)
        else:
            tenured_results.append(result)

    health = compute_onboarding_health(new_hire_results, tenured_results)
    return OnboardingHealthOut(
        team_id=team_id,
        window_days=ONBOARDING_WINDOW_DAYS,
        cohort_size=health.cohort_size,
        sufficient_data=health.sufficient_data,
        new_hire_mean=health.new_hire_mean,
        tenured_mean=health.tenured_mean,
        integration_friction=health.integration_friction,
        friction_flag=health.friction_flag,
        at_risk_count=health.at_risk_count,
        notice=health.notice,
    )
