"""Compatibility Hiring routes (Phase 9, HR Workbook v6).

Candidates, Quick Screen / Full Calibration assessments, and development plans.
Reviewer-only; every assessment is human-authored and audited. The system only
*suggests* an overall risk — it never rejects a candidate automatically.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import log_audit
from app.db import get_db
from app.deps import get_current_user
from app.hiring import (
    DECISION_GUIDANCE,
    DIMENSIONS,
    DISCLAIMER,
    OVERALL_RISK_LABELS,
    QUICK_SCREEN_SIGNALS,
    SIGNALS,
    suggest_overall_risk,
)
from app.models import (
    Candidate,
    CompatibilityAssessment,
    DevelopmentPlan,
    Role,
    User,
)
from app.schemas import (
    AssessmentCreate,
    AssessmentOut,
    CandidateCreate,
    CandidateDetailOut,
    CandidateOut,
    DevelopmentPlanCreate,
    DevelopmentPlanOut,
    HiringReferenceOut,
    SignalRef,
)

router = APIRouter(prefix="/hiring", tags=["hiring"])

# Hiring is an HR/management activity; ethics reviewers may view for oversight.
_HIRING_WRITERS = {Role.hr, Role.team_lead, Role.admin}
_HIRING_VIEWERS = {Role.hr, Role.team_lead, Role.admin, Role.ethics_reviewer}


def _require(user: User, roles: set[Role]) -> None:
    if user.role not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient role for hiring",
        )


def _assessment_out(db: Session, a: CompatibilityAssessment) -> AssessmentOut:
    reviewer_name = None
    if a.reviewer_user_id is not None:
        reviewer = db.get(User, a.reviewer_user_id)
        reviewer_name = reviewer.full_name if reviewer else None
    suggested = suggest_overall_risk(a.signals) if a.signals else None
    return AssessmentOut(
        id=a.id,
        candidate_id=a.candidate_id,
        type=a.type,
        reviewer_user_id=a.reviewer_user_id,
        reviewer_name=reviewer_name,
        signals=a.signals,
        dimensions=a.dimensions,
        overall_risk=a.overall_risk,
        suggested_overall_risk=suggested,
        recommendation=a.recommendation,
        action_items=a.action_items,
        source_of_evidence=a.source_of_evidence,
        notes=a.notes,
        created_at=a.created_at,
    )


@router.get("/reference", response_model=HiringReferenceOut)
def hiring_reference(user: User = Depends(get_current_user)) -> HiringReferenceOut:
    _require(user, _HIRING_VIEWERS)
    return HiringReferenceOut(
        signals=[SignalRef(**vars(s)) for s in SIGNALS],
        quick_screen_signals=QUICK_SCREEN_SIGNALS,
        dimensions=DIMENSIONS,
        decision_guidance=DECISION_GUIDANCE,
        overall_risk_labels={k.value: v for k, v in OVERALL_RISK_LABELS.items()},
        disclaimer=DISCLAIMER,
    )


@router.post("/candidates", response_model=CandidateOut, status_code=status.HTTP_201_CREATED)
def create_candidate(
    payload: CandidateCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Candidate:
    _require(user, _HIRING_WRITERS)
    candidate = Candidate(
        full_name=payload.full_name,
        role=payload.role,
        notes=payload.notes,
        created_by=user.id,
    )
    db.add(candidate)
    db.flush()
    log_audit(
        db,
        actor_user_id=user.id,
        action="hiring.candidate.create",
        entity_type="candidate",
        entity_id=str(candidate.id),
    )
    db.commit()
    db.refresh(candidate)
    return candidate


@router.get("/candidates", response_model=list[CandidateOut])
def list_candidates(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Candidate]:
    _require(user, _HIRING_VIEWERS)
    return list(db.scalars(select(Candidate).order_by(Candidate.created_at.desc())).all())


@router.get("/candidates/{candidate_id}", response_model=CandidateDetailOut)
def get_candidate(
    candidate_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CandidateDetailOut:
    _require(user, _HIRING_VIEWERS)
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    assessments = db.scalars(
        select(CompatibilityAssessment)
        .where(CompatibilityAssessment.candidate_id == candidate_id)
        .order_by(CompatibilityAssessment.created_at.desc())
    ).all()
    plans = db.scalars(
        select(DevelopmentPlan)
        .where(DevelopmentPlan.candidate_id == candidate_id)
        .order_by(DevelopmentPlan.created_at.desc())
    ).all()

    return CandidateDetailOut(
        candidate=CandidateOut.model_validate(candidate),
        assessments=[_assessment_out(db, a) for a in assessments],
        development_plans=[DevelopmentPlanOut.model_validate(p) for p in plans],
    )


@router.post(
    "/candidates/{candidate_id}/assessments",
    response_model=AssessmentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_assessment(
    candidate_id: uuid.UUID,
    payload: AssessmentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AssessmentOut:
    _require(user, _HIRING_WRITERS)
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    signals = {k: v.value for k, v in payload.signals.items()} if payload.signals else None
    assessment = CompatibilityAssessment(
        candidate_id=candidate_id,
        type=payload.type,
        reviewer_user_id=user.id,
        signals=signals,
        dimensions=payload.dimensions,
        overall_risk=payload.overall_risk,
        recommendation=payload.recommendation,
        action_items=payload.action_items,
        source_of_evidence=payload.source_of_evidence,
        notes=payload.notes,
    )
    db.add(assessment)
    db.flush()
    log_audit(
        db,
        actor_user_id=user.id,
        action="hiring.assessment.create",
        entity_type="compatibility_assessment",
        entity_id=str(assessment.id),
        detail={
            "candidate": str(candidate_id),
            "type": payload.type.value,
            "overall_risk": payload.overall_risk.value if payload.overall_risk else None,
        },
    )
    db.commit()
    db.refresh(assessment)
    return _assessment_out(db, assessment)


@router.post(
    "/candidates/{candidate_id}/development-plan",
    response_model=DevelopmentPlanOut,
    status_code=status.HTTP_201_CREATED,
)
def create_development_plan(
    candidate_id: uuid.UUID,
    payload: DevelopmentPlanCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DevelopmentPlan:
    _require(user, _HIRING_WRITERS)
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    plan = DevelopmentPlan(
        candidate_id=candidate_id,
        risk_area=payload.risk_area,
        observed_pattern=payload.observed_pattern,
        suggested_support=payload.suggested_support,
        review_date=payload.review_date,
        progress_notes=payload.progress_notes,
        created_by=user.id,
    )
    db.add(plan)
    db.flush()
    log_audit(
        db,
        actor_user_id=user.id,
        action="hiring.development_plan.create",
        entity_type="development_plan",
        entity_id=str(plan.id),
        detail={"candidate": str(candidate_id)},
    )
    db.commit()
    db.refresh(plan)
    return plan
