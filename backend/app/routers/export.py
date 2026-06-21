"""Human-review export (Phase 6): one explainable bundle per employee.

Packages everything a human reviewer needs — profile, questionnaire history,
recalibration timeline, calibration reviews — so decisions are made by people on
complete, explainable evidence. Subjects can export their own data (portability);
reviewers can export within their scope. Every export is audited.
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import log_audit
from app.db import get_db
from app.deps import get_current_user
from app.models import CalibrationReview, Questionnaire, Role, User
from app.routers.questionnaire import questionnaire_result
from app.routers.recalibration import build_timeline
from app.schemas import (
    CalibrationReviewOut,
    ExportBundleOut,
    UserRead,
)

router = APIRouter(tags=["export"])

_REVIEWER_ROLES = {Role.hr, Role.team_lead, Role.admin, Role.ethics_reviewer}

_DISCLAIMER_RU = (
    "Экспорт для проверки человеком. Содержит объяснимые данные среды и не является "
    "автоматическим решением. Любые выводы делает человек."
)


@router.get("/export/employee/{employee_id}", response_model=ExportBundleOut)
def export_employee(
    employee_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExportBundleOut:
    subject = db.get(User, employee_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    # Subject (own data) or a reviewer in scope.
    if employee_id != user.id:
        if user.role not in _REVIEWER_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not allowed to export this employee's data",
            )
        if user.role == Role.team_lead and subject.team_id != user.team_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Team leads may only export their own team",
            )

    questionnaires = db.scalars(
        select(Questionnaire)
        .where(Questionnaire.user_id == employee_id)
        .order_by(Questionnaire.submitted_at.desc())
    ).all()

    reviews = db.scalars(
        select(CalibrationReview)
        .where(CalibrationReview.subject_user_id == employee_id)
        .order_by(CalibrationReview.created_at.desc())
    ).all()
    reviewer_names: dict[uuid.UUID, str] = {}
    for review in reviews:
        rid = review.reviewer_user_id
        if rid is not None and rid not in reviewer_names:
            reviewer = db.get(User, rid)
            if reviewer is not None:
                reviewer_names[rid] = reviewer.full_name

    log_audit(
        db,
        actor_user_id=user.id,
        action="export.employee",
        entity_type="user",
        entity_id=str(employee_id),
        detail={"questionnaires": len(questionnaires), "reviews": len(reviews)},
    )
    db.commit()

    return ExportBundleOut(
        generated_at=datetime.now(UTC),
        disclaimer=_DISCLAIMER_RU,
        user=UserRead.model_validate(subject),
        questionnaires=[questionnaire_result(q, viewer_role=user.role.value) for q in questionnaires],
        recalibration=build_timeline(db, employee_id),
        calibration_reviews=[
            CalibrationReviewOut(
                id=r.id,
                subject_user_id=r.subject_user_id,
                reviewer_user_id=r.reviewer_user_id,
                reviewer_name=reviewer_names.get(r.reviewer_user_id),
                risk_level=r.risk_level,
                recommendation=r.recommendation,
                action_items=r.action_items,
                source_of_evidence=r.source_of_evidence,
                notes=r.notes,
                created_at=r.created_at,
            )
            for r in reviews
        ],
    )
