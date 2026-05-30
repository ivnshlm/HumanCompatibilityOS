"""Calibration review routes (Phase 5): human review of operational risk.

Per doctrine, the system never decides — a human reviewer (HR / Team Lead /
Admin / Ethics Reviewer) records an explainable review with the source of
evidence. The subject can always read reviews about themselves (transparency).
Every create and read is audited.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import log_audit
from app.db import get_db
from app.deps import get_current_user
from app.models import CalibrationReview, Role, User
from app.schemas import CalibrationReviewCreate, CalibrationReviewOut

router = APIRouter(prefix="/calibration", tags=["calibration"])

_REVIEWER_ROLES = {Role.hr, Role.team_lead, Role.admin, Role.ethics_reviewer}


def _ensure_can_review(actor: User, subject: User) -> None:
    if actor.role not in _REVIEWER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient role to record a calibration review",
        )
    if actor.role == Role.team_lead and subject.team_id != actor.team_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Team leads may only review their own team",
        )


def _to_out(review: CalibrationReview, reviewer_name: str | None) -> CalibrationReviewOut:
    return CalibrationReviewOut(
        id=review.id,
        subject_user_id=review.subject_user_id,
        reviewer_user_id=review.reviewer_user_id,
        reviewer_name=reviewer_name,
        risk_level=review.risk_level,
        recommendation=review.recommendation,
        action_items=review.action_items,
        source_of_evidence=review.source_of_evidence,
        notes=review.notes,
        created_at=review.created_at,
    )


@router.post("/review", response_model=CalibrationReviewOut, status_code=status.HTTP_201_CREATED)
def create_review(
    payload: CalibrationReviewCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CalibrationReviewOut:
    subject = db.get(User, payload.subject_user_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

    _ensure_can_review(user, subject)

    review = CalibrationReview(
        subject_user_id=payload.subject_user_id,
        reviewer_user_id=user.id,
        risk_level=payload.risk_level,
        recommendation=payload.recommendation,
        action_items=payload.action_items,
        source_of_evidence=payload.source_of_evidence,
        notes=payload.notes,
    )
    db.add(review)
    db.flush()
    log_audit(
        db,
        actor_user_id=user.id,
        action="calibration.review.create",
        entity_type="calibration_review",
        entity_id=str(review.id),
        detail={
            "subject": str(payload.subject_user_id),
            "risk_level": payload.risk_level.value if payload.risk_level else None,
        },
    )
    db.commit()
    db.refresh(review)
    return _to_out(review, user.full_name)


@router.get("/review/{subject_user_id}", response_model=list[CalibrationReviewOut])
def list_reviews(
    subject_user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CalibrationReviewOut]:
    # Subjects may always read reviews about themselves (transparency).
    if subject_user_id != user.id:
        subject = db.get(User, subject_user_id)
        if subject is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
        _ensure_can_review(user, subject)

    rows = db.scalars(
        select(CalibrationReview)
        .where(CalibrationReview.subject_user_id == subject_user_id)
        .order_by(CalibrationReview.created_at.desc())
    ).all()

    # Resolve reviewer display names (small N per subject).
    reviewer_names: dict[uuid.UUID, str] = {}
    for review in rows:
        rid = review.reviewer_user_id
        if rid is not None and rid not in reviewer_names:
            reviewer = db.get(User, rid)
            if reviewer is not None:
                reviewer_names[rid] = reviewer.full_name

    log_audit(
        db,
        actor_user_id=user.id,
        action="calibration.review.view",
        entity_type="user",
        entity_id=str(subject_user_id),
        detail={"count": len(rows)},
    )
    db.commit()

    return [_to_out(r, reviewer_names.get(r.reviewer_user_id)) for r in rows]
