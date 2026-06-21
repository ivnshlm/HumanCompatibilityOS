"""Questionnaire submission, scoring, and per-employee history."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import question_bank
from app.audit import log_audit
from app.db import get_db
from app.deps import get_current_user
from app.interpretation import build_interpretation, build_report_layer
from app.models import Questionnaire, QuestionnaireAnswer, Role, User
from app.schemas import (
    ComponentScoreOut,
    DominantFactorOut,
    HistoryItem,
    InterpretationOut,
    LayerNoteOut,
    QuestionnaireResult,
    QuestionnaireSubmit,
    QuestionOut,
    QuestionSet,
    ReportLayerOut,
    ScaleOption,
)
from app.scoring import BurnoutResult, compute_burnout_score

router = APIRouter(tags=["questionnaire"])

# Roles allowed to view another employee's history / individual result.
_REVIEWER_ROLES = {Role.hr, Role.team_lead, Role.admin, Role.ethics_reviewer}


def _interpretation_out(result: BurnoutResult, answers: dict[str, int]) -> InterpretationOut:
    interp = build_interpretation(result, answers)
    return InterpretationOut(
        summary=interp.summary,
        dominant_factors=[
            DominantFactorOut(
                key=f.key,
                title=f.title,
                score=f.score,
                explanation=f.explanation,
                subdimension=f.subdimension,
            )
            for f in interp.dominant_factors
        ],
        possible_meaning=interp.possible_meaning,
        check_next=interp.check_next,
        disclaimer=interp.disclaimer,
        follow_ups=interp.follow_ups,
    )


def _report_layer_out(result: BurnoutResult, viewer_role: str | None) -> ReportLayerOut | None:
    layer = build_report_layer(result, viewer_role)
    if layer is None:
        return None
    return ReportLayerOut(
        layer=layer.layer,
        label=layer.label,
        description=layer.description,
        notes=[LayerNoteOut(component=n.component, label=n.label, note=n.note) for n in layer.notes],
    )


def _result_response(
    q: Questionnaire,
    result: BurnoutResult,
    answers: dict[str, int],
    viewer_role: str | None = None,
) -> QuestionnaireResult:
    """Assemble the full explainable result (components + interpretation)."""
    return QuestionnaireResult(
        id=q.id,
        user_id=q.user_id,
        type=q.type,
        session_level=q.session_level,
        submitted_at=q.submitted_at,
        burnout_pressure_score=result.burnout_pressure,
        risk_level=result.risk_level,
        components=[
            ComponentScoreOut(
                component=c.component.value,
                label=c.label,
                weight=c.weight,
                score=c.score,
                question_ids=c.question_ids,
            )
            for c in result.components
        ],
        interpretation=_interpretation_out(result, answers),
        report_layer=_report_layer_out(result, viewer_role),
    )


def questionnaire_result(q: Questionnaire, viewer_role: str | None = None) -> QuestionnaireResult:
    """Rebuild the full explainable result for a stored questionnaire.

    Recomputes from the persisted answers so historical entries carry the same
    components + interpretation as a fresh submission (reused by the detail
    endpoint and the human-review export). ``viewer_role`` selects the review
    report layer (None / participant adds nothing beyond the base reading).
    """
    answers = {a.question_id: a.value for a in q.answers}
    return _result_response(q, compute_burnout_score(answers), answers, viewer_role)


@router.get("/questionnaire/questions", response_model=QuestionSet)
def list_questions(level: str = "short") -> QuestionSet:
    """Return a selected question set for a session level (short/base/deep).

    Selection is deterministic (see question_bank.select_session) so the set is
    stable and comparable. Defaults to the short (15-question) session.
    """
    if level not in question_bank.LEVELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown session level: {level}",
        )
    questions = []
    for qid in question_bank.select_session(level):
        bq = question_bank.get(qid)
        questions.append(
            QuestionOut(
                question_id=bq.question_id,
                text=bq.question_text,
                component=bq.component_id,
                component_name=bq.component_name,
                subdimension=bq.subdimension,
                reverse=bq.reverse_scored,
                follow_up_question=bq.follow_up_question,
            )
        )
    scale = [ScaleOption(**opt) for opt in question_bank.scale()]
    return QuestionSet(level=level, scale=scale, questions=questions)


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

    answers = {a.question_id: a.value for a in payload.answers}
    if len(answers) != len(payload.answers):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duplicate question_id")

    try:
        result = compute_burnout_score(answers)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    questionnaire = Questionnaire(
        user_id=user.id,
        type=payload.type,
        session_level=payload.session_level,
        question_bank_version=question_bank.bank_version(),
        burnout_pressure_score=result.burnout_pressure,
        risk_level=result.risk_level,
    )
    questionnaire.answers = [
        QuestionnaireAnswer(question_id=qid, value=value) for qid, value in answers.items()
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

    return _result_response(questionnaire, result, answers)


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


@router.get("/questionnaire/{questionnaire_id}", response_model=QuestionnaireResult)
def questionnaire_detail(
    questionnaire_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuestionnaireResult:
    """Full explainable detail of one past result (number + components + interpretation).

    Subject may always see their own; reviewers may see anyone's. Every view is
    audited — opening an individual result is accountable, not silent profiling.
    """
    q = db.get(Questionnaire, questionnaire_id)
    if q is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Questionnaire not found")
    if q.user_id != user.id and user.role not in _REVIEWER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to view this result",
        )

    log_audit(
        db,
        actor_user_id=user.id,
        action="questionnaire.view",
        entity_type="questionnaire",
        entity_id=str(q.id),
        detail={"subject_user_id": str(q.user_id)},
    )
    db.commit()
    return questionnaire_result(q, viewer_role=user.role.value)
