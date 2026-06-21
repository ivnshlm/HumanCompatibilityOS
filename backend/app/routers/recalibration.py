"""Recalibration routes (Phase 4): create cycle events, view trend timeline.

Cycle baseline → 30d → 90d → retrospective. Compares later cycles against the
baseline and surfaces advisory development recommendations for human review.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import log_audit
from app.db import get_db
from app.deps import get_current_user
from app.models import (
    Questionnaire,
    RecalibrationCycle,
    RecalibrationEvent,
    Role,
    User,
)
from app.recalibration import (
    TREND_LABELS_RU,
    recommendations_for,
    trend_for,
)
from app.schemas import (
    RecalibrationCreate,
    RecalibrationEventOut,
    RecalibrationTimelineOut,
)
from app.scoring import BurnoutResult, compute_burnout_score

router = APIRouter(prefix="/recalibration", tags=["recalibration"])

_REVIEWER_ROLES = {Role.hr, Role.team_lead, Role.admin, Role.ethics_reviewer}


def _can_access_subject(actor: User, subject_id: uuid.UUID) -> bool:
    return actor.id == subject_id or actor.role in _REVIEWER_ROLES


def _result_for(questionnaire: Questionnaire | None) -> BurnoutResult | None:
    if questionnaire is None:
        return None
    answers = {a.question_id: a.value for a in questionnaire.answers}
    try:
        return compute_burnout_score(answers)
    except ValueError:
        return None


def _baseline_score(db: Session, user_id: uuid.UUID) -> float | None:
    """Burnout score anchored by the earliest baseline-cycle event, if any."""
    event = db.scalar(
        select(RecalibrationEvent)
        .where(
            RecalibrationEvent.user_id == user_id,
            RecalibrationEvent.cycle == RecalibrationCycle.baseline,
        )
        .order_by(RecalibrationEvent.created_at.asc())
        .limit(1)
    )
    if event is None or event.questionnaire_id is None:
        return None
    q = db.get(Questionnaire, event.questionnaire_id)
    return q.burnout_pressure_score if q is not None else None


@router.post("/create", response_model=RecalibrationEventOut, status_code=status.HTTP_201_CREATED)
def create_recalibration(
    payload: RecalibrationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecalibrationEventOut:
    if not _can_access_subject(user, payload.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to create recalibration for this user",
        )

    subject = db.get(User, payload.user_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Resolve the anchor questionnaire: explicit id (must belong to the subject)
    # or the subject's latest scored questionnaire.
    if payload.questionnaire_id is not None:
        questionnaire = db.get(Questionnaire, payload.questionnaire_id)
        if questionnaire is None or questionnaire.user_id != payload.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Questionnaire does not belong to this user",
            )
    else:
        questionnaire = db.scalar(
            select(Questionnaire)
            .where(
                Questionnaire.user_id == payload.user_id,
                Questionnaire.burnout_pressure_score.is_not(None),
            )
            .order_by(Questionnaire.submitted_at.desc())
            .limit(1)
        )
        if questionnaire is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User has no scored questionnaire to anchor recalibration",
            )

    baseline = _baseline_score(db, payload.user_id)

    event = RecalibrationEvent(
        user_id=payload.user_id,
        questionnaire_id=questionnaire.id,
        cycle=payload.cycle,
        notes=payload.notes,
    )
    db.add(event)
    db.flush()
    log_audit(
        db,
        actor_user_id=user.id,
        action="recalibration.create",
        entity_type="recalibration_event",
        entity_id=str(event.id),
        detail={"subject": str(payload.user_id), "cycle": payload.cycle.value},
    )
    db.commit()
    db.refresh(event)

    score = questionnaire.burnout_pressure_score
    delta = (
        round(score - baseline, 2)
        if score is not None and baseline is not None and payload.cycle != RecalibrationCycle.baseline
        else None
    )
    return RecalibrationEventOut(
        id=event.id,
        cycle=event.cycle,
        questionnaire_id=event.questionnaire_id,
        submitted_at=questionnaire.submitted_at,
        burnout_pressure_score=score,
        risk_level=questionnaire.risk_level,
        delta_vs_baseline=delta,
        notes=event.notes,
        created_at=event.created_at,
    )


def build_timeline(db: Session, user_id: uuid.UUID) -> RecalibrationTimelineOut:
    """Assemble a user's recalibration timeline (shared by the GET route and export)."""
    events = list(
        db.scalars(
            select(RecalibrationEvent)
            .where(RecalibrationEvent.user_id == user_id)
            .order_by(RecalibrationEvent.created_at.asc())
        ).all()
    )

    baseline = _baseline_score(db, user_id)

    event_outs: list[RecalibrationEventOut] = []
    latest_questionnaire: Questionnaire | None = None
    latest_comparison_score: float | None = None
    for event in events:
        questionnaire = (
            db.get(Questionnaire, event.questionnaire_id)
            if event.questionnaire_id is not None
            else None
        )
        if questionnaire is not None:
            latest_questionnaire = questionnaire
            if event.cycle != RecalibrationCycle.baseline:
                latest_comparison_score = questionnaire.burnout_pressure_score

        score = questionnaire.burnout_pressure_score if questionnaire is not None else None
        delta = (
            round(score - baseline, 2)
            if score is not None and baseline is not None and event.cycle != RecalibrationCycle.baseline
            else None
        )
        event_outs.append(
            RecalibrationEventOut(
                id=event.id,
                cycle=event.cycle,
                questionnaire_id=event.questionnaire_id,
                submitted_at=questionnaire.submitted_at if questionnaire is not None else None,
                burnout_pressure_score=score,
                risk_level=questionnaire.risk_level if questionnaire is not None else None,
                delta_vs_baseline=delta,
                notes=event.notes,
                created_at=event.created_at,
            )
        )

    trend = trend_for(baseline, latest_comparison_score)
    result = _result_for(latest_questionnaire)
    recommendations = recommendations_for(result) if result is not None else []

    return RecalibrationTimelineOut(
        user_id=user_id,
        baseline_score=baseline,
        trend=trend.value,
        trend_label=TREND_LABELS_RU[trend],
        recommendations=recommendations,
        events=event_outs,
    )


@router.get("/{user_id}", response_model=RecalibrationTimelineOut)
def recalibration_timeline(
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecalibrationTimelineOut:
    if not _can_access_subject(user, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to view this user's recalibration history",
        )
    return build_timeline(db, user_id)
