"""Pydantic request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import RecalibrationCycle, RiskLevel, Role


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)  # bcrypt truncates beyond 72 bytes
    full_name: str = Field(min_length=1, max_length=200)
    role: Role = Role.employee
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


class QuestionnaireResult(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    type: str
    submitted_at: datetime
    burnout_pressure_score: float
    risk_level: RiskLevel
    components: list[ComponentScoreOut]


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
