"""Dashboard & environment telemetry routes (Phase 3).

Aggregate, RBAC-gated views only — no per-individual exposure. Every read is
audited (anti-surveillance: we record *who* looked at team aggregates).
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import log_audit
from app.dashboard import aggregate_metrics, aggregate_team
from app.db import get_db
from app.deps import get_current_user
from app.models import EnvironmentMetric, Questionnaire, Role, User
from app.schemas import (
    BlockAggregateOut,
    EnvironmentMetricIn,
    EnvironmentMetricOut,
    EnvironmentMetricsResponse,
    MetricAggregateOut,
    TeamDashboardOut,
)
from app.scoring import compute_burnout_score

router = APIRouter(tags=["dashboard"])

# Roles allowed to view aggregate dashboards / telemetry.
_DASHBOARD_ROLES = {Role.hr, Role.team_lead, Role.admin, Role.ethics_reviewer}
# Roles allowed to record environment metrics.
_METRIC_WRITERS = {Role.hr, Role.team_lead, Role.admin}


def _require_team_visibility(user: User, team_id: uuid.UUID | None) -> None:
    """RBAC: dashboards are management views; team leads see only their own team."""
    if user.role not in _DASHBOARD_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient role to view dashboards",
        )
    if user.role == Role.team_lead and team_id is not None and user.team_id != team_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Team leads may only view their own team",
        )


@router.get("/dashboard/team/{team_id}", response_model=TeamDashboardOut)
def team_dashboard(
    team_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TeamDashboardOut:
    _require_team_visibility(user, team_id)

    members = db.scalars(select(User).where(User.team_id == team_id)).all()
    results = []
    for member in members:
        latest = db.scalar(
            select(Questionnaire)
            .where(
                Questionnaire.user_id == member.id,
                Questionnaire.burnout_pressure_score.is_not(None),
            )
            .order_by(Questionnaire.submitted_at.desc())
            .limit(1)
        )
        if latest is None:
            continue
        answers = {a.question_index: a.value for a in latest.answers}
        try:
            results.append(compute_burnout_score(answers))
        except ValueError:
            # Skip malformed/incomplete historical rows rather than fail the view.
            continue

    dashboard = aggregate_team(results)

    log_audit(
        db,
        actor_user_id=user.id,
        action="dashboard.team.view",
        entity_type="team",
        entity_id=str(team_id),
        detail={"cohort_size": dashboard.cohort_size, "sufficient_data": dashboard.sufficient_data},
    )
    db.commit()

    return TeamDashboardOut(
        team_id=team_id,
        generated_at=datetime.now(UTC),
        cohort_size=dashboard.cohort_size,
        sufficient_data=dashboard.sufficient_data,
        interpretation="Выше — больше риска. Среда-агрегаты, не основание для кадровых решений.",
        blocks=[
            BlockAggregateOut(
                block=b.block.value,
                label=b.label,
                label_en=b.label_en,
                score=b.score,
                risk_level=b.risk_level,
                distribution=b.distribution,
            )
            for b in dashboard.blocks
        ],
        notice=dashboard.notice,
    )


@router.post(
    "/environment/metrics",
    response_model=EnvironmentMetricOut,
    status_code=status.HTTP_201_CREATED,
)
def record_environment_metric(
    payload: EnvironmentMetricIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EnvironmentMetric:
    if user.role not in _METRIC_WRITERS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient role to record environment metrics",
        )
    if user.role == Role.team_lead and payload.team_id is not None and user.team_id != payload.team_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Team leads may only record metrics for their own team",
        )

    metric = EnvironmentMetric(
        metric_type=payload.metric_type,
        value=payload.value,
        team_id=payload.team_id,
        user_id=payload.user_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
    )
    db.add(metric)
    db.flush()
    log_audit(
        db,
        actor_user_id=user.id,
        action="environment.metric.record",
        entity_type="environment_metric",
        entity_id=str(metric.id),
        detail={"metric_type": metric.metric_type, "team_id": str(payload.team_id) if payload.team_id else None},
    )
    db.commit()
    db.refresh(metric)
    return metric


@router.get("/environment/metrics", response_model=EnvironmentMetricsResponse)
def environment_metrics(
    team_id: uuid.UUID | None = None,
    metric_type: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EnvironmentMetricsResponse:
    _require_team_visibility(user, team_id)
    # Team leads always scope to their own team, even without an explicit filter.
    if user.role == Role.team_lead:
        team_id = user.team_id

    stmt = select(EnvironmentMetric)
    if team_id is not None:
        stmt = stmt.where(EnvironmentMetric.team_id == team_id)
    if metric_type is not None:
        stmt = stmt.where(EnvironmentMetric.metric_type == metric_type)

    rows = list(db.scalars(stmt).all())
    aggregates = aggregate_metrics(rows)

    return EnvironmentMetricsResponse(
        team_id=team_id,
        metric_type=metric_type,
        aggregates=[
            MetricAggregateOut(
                metric_type=a.metric_type,
                count=a.count,
                mean=a.mean,
                minimum=a.minimum,
                maximum=a.maximum,
            )
            for a in aggregates
        ],
    )
