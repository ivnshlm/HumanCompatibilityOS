"""Pydantic request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import RiskLevel, Role


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
