"""Pydantic request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import AssessmentType, OverallRisk, RecalibrationCycle, RiskLevel, Role


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)  # bcrypt truncates beyond 72 bytes
    full_name: str = Field(min_length=1, max_length=200)
    # Role is NOT client-settable — registration always creates an Employee.
    # Privileged roles are granted only by an admin (see AdminUserUpdate) or the
    # INITIAL_ADMIN_EMAILS bootstrap. A self-chosen role would be privilege escalation.
    team_id: uuid.UUID | None = None


class AdminUserUpdate(BaseModel):
    """Admin-only mutation of a user. Only the provided fields are applied
    (detected via model_fields_set, so team_id=null explicitly clears the team)."""

    role: Role | None = None
    is_active: bool | None = None
    team_id: uuid.UUID | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: Role
    team_id: uuid.UUID | None
    is_active: bool
    consent_given: bool
    consent_at: datetime | None
    created_at: datetime


class ConsentRequest(BaseModel):
    consent_given: bool = True


# --- Questionnaire & scoring ---


class QuestionOut(BaseModel):
    index: int
    text: str
    component: str
    reverse: bool


class AnswerIn(BaseModel):
    question_index: int = Field(ge=1, le=15)
    value: int = Field(ge=1, le=5)


class QuestionnaireSubmit(BaseModel):
    type: str = "burnout"
    answers: list[AnswerIn] = Field(min_length=1)


class ComponentScoreOut(BaseModel):
    component: str
    label: str
    weight: float
    score: float
    question_indices: list[int]


class DominantFactorOut(BaseModel):
    key: str
    title: str
    score: float
    explanation: str


class InterpretationOut(BaseModel):
    summary: str
    dominant_factors: list[DominantFactorOut]
    possible_meaning: str
    check_next: list[str]
    disclaimer: str


class QuestionnaireResult(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    type: str
    submitted_at: datetime
    burnout_pressure_score: float
    risk_level: RiskLevel
    components: list[ComponentScoreOut]
    interpretation: InterpretationOut


class HistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    submitted_at: datetime
    burnout_pressure_score: float | None
    risk_level: RiskLevel | None


# --- Dashboard (telemetry) ---


class BlockAggregateOut(BaseModel):
    block: str
    label: str
    label_en: str
    score: float
    risk_level: RiskLevel
    distribution: dict[str, int]


class TeamDashboardOut(BaseModel):
    team_id: uuid.UUID
    generated_at: datetime
    cohort_size: int
    sufficient_data: bool
    interpretation: str
    blocks: list[BlockAggregateOut]
    notice: str | None = None


# --- Environment metrics ---


class EnvironmentMetricIn(BaseModel):
    metric_type: str = Field(min_length=1, max_length=80)
    value: float
    team_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None


class EnvironmentMetricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    metric_type: str
    value: float
    team_id: uuid.UUID | None
    user_id: uuid.UUID | None
    period_start: datetime | None
    period_end: datetime | None
    created_at: datetime


class MetricAggregateOut(BaseModel):
    metric_type: str
    count: int
    mean: float
    minimum: float
    maximum: float


class EnvironmentMetricsResponse(BaseModel):
    team_id: uuid.UUID | None = None
    metric_type: str | None = None
    aggregates: list[MetricAggregateOut]


# --- Recalibration ---


class RecalibrationCreate(BaseModel):
    user_id: uuid.UUID
    cycle: RecalibrationCycle
    # Anchor questionnaire; defaults to the user's latest scored one if omitted.
    questionnaire_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)


class RecalibrationEventOut(BaseModel):
    id: uuid.UUID
    cycle: RecalibrationCycle
    questionnaire_id: uuid.UUID | None
    submitted_at: datetime | None
    burnout_pressure_score: float | None
    risk_level: RiskLevel | None
    delta_vs_baseline: float | None
    notes: str | None
    created_at: datetime


class RecalibrationTimelineOut(BaseModel):
    user_id: uuid.UUID
    baseline_score: float | None
    trend: str
    trend_label: str
    recommendations: list[str]
    events: list[RecalibrationEventOut]


# --- User directory (reviewer-scoped) ---


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: EmailStr
    role: Role
    team_id: uuid.UUID | None


# --- Calibration review (human review of risk) ---


class CalibrationReviewCreate(BaseModel):
    subject_user_id: uuid.UUID
    risk_level: RiskLevel | None = None
    recommendation: str | None = Field(default=None, max_length=500)
    action_items: str | None = Field(default=None, max_length=2000)
    source_of_evidence: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)


class CalibrationReviewOut(BaseModel):
    id: uuid.UUID
    subject_user_id: uuid.UUID
    reviewer_user_id: uuid.UUID | None
    reviewer_name: str | None
    risk_level: RiskLevel | None
    recommendation: str | None
    action_items: str | None
    source_of_evidence: str | None
    notes: str | None
    created_at: datetime


# --- Ethics / compliance / pilot (Phase 6) ---


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    action: str
    entity_type: str | None
    entity_id: str | None
    detail: dict | None
    created_at: datetime


class CompliancePolicyOut(BaseModel):
    principles: list[str]
    no_automated_decisions: bool
    requires_consent: bool
    requires_human_review: bool
    pilot_metric: str
    pilot_target_pct: float
    disclaimer: str


class MetricChangeOut(BaseModel):
    key: str
    label: str
    baseline_mean: float
    latest_mean: float
    pct_change: float
    improved: bool


class PilotMetricOut(BaseModel):
    team_id: uuid.UUID
    cohort_size: int
    sufficient_data: bool
    target_pct: float
    target_met: bool
    headline: MetricChangeOut | None = None
    blocks: list[MetricChangeOut] = []
    notice: str | None = None


class OnboardingHealthOut(BaseModel):
    team_id: uuid.UUID
    window_days: int
    cohort_size: int
    sufficient_data: bool
    new_hire_mean: float | None
    tenured_mean: float | None
    integration_friction: float | None
    friction_flag: bool
    at_risk_count: int
    notice: str | None = None


class ExportBundleOut(BaseModel):
    generated_at: datetime
    disclaimer: str
    user: UserRead
    # Full explainable results (components + interpretation), not bare summaries —
    # a human reviewer gets the same careful reading the employee sees.
    questionnaires: list[QuestionnaireResult]
    recalibration: RecalibrationTimelineOut
    calibration_reviews: list[CalibrationReviewOut]


# --- Compatibility Hiring (HR Workbook v6) ---


class SignalRef(BaseModel):
    key: str
    label: str
    label_en: str
    indicator: str
    question: str
    focus: str
    legend_low: str
    legend_medium: str
    legend_high: str
    quick_screen: bool


class HiringReferenceOut(BaseModel):
    signals: list[SignalRef]
    quick_screen_signals: list[str]
    dimensions: list[dict[str, str]]
    decision_guidance: list[str]
    overall_risk_labels: dict[str, str]
    disclaimer: str


class CandidateCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    role: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    role: str | None
    notes: str | None
    created_at: datetime


class AssessmentCreate(BaseModel):
    type: AssessmentType
    signals: dict[str, RiskLevel] | None = None
    dimensions: dict[str, str] | None = None
    overall_risk: OverallRisk | None = None
    recommendation: str | None = Field(default=None, max_length=500)
    action_items: str | None = Field(default=None, max_length=2000)
    source_of_evidence: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)


class AssessmentOut(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    type: AssessmentType
    reviewer_user_id: uuid.UUID | None
    reviewer_name: str | None
    signals: dict[str, str] | None
    dimensions: dict[str, str] | None
    overall_risk: OverallRisk | None
    suggested_overall_risk: OverallRisk | None
    recommendation: str | None
    action_items: str | None
    source_of_evidence: str | None
    notes: str | None
    created_at: datetime


class DevelopmentPlanCreate(BaseModel):
    risk_area: str | None = Field(default=None, max_length=200)
    observed_pattern: str | None = Field(default=None, max_length=2000)
    suggested_support: str | None = Field(default=None, max_length=2000)
    review_date: datetime | None = None
    progress_notes: str | None = Field(default=None, max_length=2000)


class DevelopmentPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    risk_area: str | None
    observed_pattern: str | None
    suggested_support: str | None
    review_date: datetime | None
    progress_notes: str | None
    created_at: datetime


class CandidateDetailOut(BaseModel):
    candidate: CandidateOut
    assessments: list[AssessmentOut]
    development_plans: list[DevelopmentPlanOut]
