"""Questionnaire submission, scoring, and per-employee history."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import log_audit
from app.db import get_db
from app.deps import get_current_user
from app.models import Questionnaire, QuestionnaireAnswer, Role, User
from app.interpretation import build_interpretation
from app.schemas import (
    ComponentScoreOut,
    DominantFactorOut,
    HistoryItem,
    InterpretationOut,
    QuestionnaireResult,
    QuestionnaireSubmit,
    QuestionOut,
)
from app.scoring import QUESTIONS, BurnoutResult, compute_burnout_score


def _interpretation_out(result: BurnoutResult) -> InterpretationOut:
    interp = build_interpretation(result)
    return InterpretationOut(
        summary=interp.summary,
        dominant_factors=[
            DominantFactorOut(key=f.key, title=f.title, score=f.score, explanation=f.explanation)
            for f in interp.dominant_factors
        ],
        possible_meaning=interp.possible_meaning,
        check_next=interp.check_next,
        disclaimer=interp.disclaimer,
    )

router = APIRouter(tags=["questionnaire"])

# Roles allowed to view another employee's history.
_REVIEWER_ROLES = {Role.hr, Role.team_lead, Role.admin, Role.ethics_reviewer}


@router.get("/questionnaire/questions", response_model=list[QuestionOut])
def list_questions() -> list[QuestionOut]:
    return [
        QuestionOut(index=q.index, text=q.text, component=q.component.value, reverse=q.reverse)
        for q in QUESTIONS
    ]


@router.post(
    "/questionnaire/submit",
    response_model=QuestionnaireResult,
    status_code=status.HTTP_201_CREATED,
)
def submit_questionnaire(
    payload: QuestionnaireSubmit,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuestionnaireResult:
    # Ethics doctrine: no operational data collection without explicit consent.
    if not user.consent_given:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Consent required before submitting operational data",
        )

    answers = {a.question_index: a.value for a in payload.answers}
    if len(answers) != len(payload.answers):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duplicate question_index")

    try:
        result = compute_burnout_score(answers)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    questionnaire = Questionnaire(
        user_id=user.id,
        type=payload.type,
        burnout_pressure_score=result.burnout_pressure,
        risk_level=result.risk_level,
    )
    questionnaire.answers = [
        QuestionnaireAnswer(question_index=idx, value=value) for idx, value in answers.items()
    ]
    db.add(questionnaire)
    db.flush()
    log_audit(
        db,
        actor_user_id=user.id,
        action="questionnaire.submit",
        entity_type="questionnaire",
        entity_id=str(questionnaire.id),
        detail={"risk_level": result.risk_level.value, "score": result.burnout_pressure},
    )
    db.commit()
    db.refresh(questionnaire)

    return QuestionnaireResult(
        id=questionnaire.id,
        user_id=user.id,
        type=questionnaire.type,
        submitted_at=questionnaire.submitted_at,
        burnout_pressure_score=result.burnout_pressure,
        risk_level=result.risk_level,
        components=[
            ComponentScoreOut(
                component=c.component.value,
                label=c.label,
                weight=c.weight,
                score=c.score,
                question_indices=c.question_indices,
            )
            for c in result.components
        ],
        interpretation=_interpretation_out(result),
    )


@router.get("/employee/{employee_id}/history", response_model=list[HistoryItem])
def employee_history(
    employee_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Questionnaire]:
    # An employee may always see their own history; reviewers may see anyone's.
    if employee_id != user.id and user.role not in _REVIEWER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to view this employee's history",
        )

    rows = db.scalars(
        select(Questionnaire)
        .where(Questionnaire.user_id == employee_id)
        .order_by(Questionnaire.submitted_at.desc())
    ).all()
    return list(rows)
