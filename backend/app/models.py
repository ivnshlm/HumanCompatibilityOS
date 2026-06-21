"""SQLAlchemy ORM models for Human Compatibility OS.

Six domain tables from the spec — users, questionnaires, questionnaire_answers,
calibration_reviews, recalibration_events, environment_metrics — plus audit_logs
(required by the ethics doctrine).
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db import Base


class Role(str, enum.Enum):
    employee = "employee"
    hr = "hr"
    team_lead = "team_lead"
    admin = "admin"  # Founder / Admin
    ethics_reviewer = "ethics_reviewer"


class RiskLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class RecalibrationCycle(str, enum.Enum):
    baseline = "baseline"
    day_30 = "day_30"
    day_90 = "day_90"
    retrospective = "retrospective"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False), default=Role.employee, nullable=False)
    # Lightweight team grouping key (no dedicated teams table in the MVP spec).
    team_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    consent_given: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    questionnaires: Mapped[list["Questionnaire"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Questionnaire(Base):
    __tablename__ = "questionnaires"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type: Mapped[str] = mapped_column(String(50), default="burnout", nullable=False)
    # Question Bank session: which level (short/base/deep) and bank version were used.
    session_level: Mapped[str | None] = mapped_column(String(10), nullable=True)
    question_bank_version: Mapped[str | None] = mapped_column(String(20), nullable=True)

    burnout_pressure_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[RiskLevel | None] = mapped_column(Enum(RiskLevel, native_enum=False), nullable=True)

    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="questionnaires")
    answers: Mapped[list["QuestionnaireAnswer"]] = relationship(
        back_populates="questionnaire", cascade="all, delete-orphan"
    )


class QuestionnaireAnswer(Base):
    __tablename__ = "questionnaire_answers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    questionnaire_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("questionnaires.id", ondelete="CASCADE"), index=True, nullable=False
    )
    question_id: Mapped[str] = mapped_column(String(40), nullable=False)  # bank id, e.g. HCO_DA_001
    value: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..5

    questionnaire: Mapped["Questionnaire"] = relationship(back_populates="answers")


class CalibrationReview(Base):
    __tablename__ = "calibration_reviews"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    subject_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    risk_level: Mapped[RiskLevel | None] = mapped_column(Enum(RiskLevel, native_enum=False), nullable=True)
    recommendation: Mapped[str | None] = mapped_column(String(500), nullable=True)
    action_items: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_of_evidence: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RecalibrationEvent(Base):
    __tablename__ = "recalibration_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    questionnaire_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("questionnaires.id", ondelete="SET NULL"), nullable=True
    )
    cycle: Mapped[RecalibrationCycle] = mapped_column(
        Enum(RecalibrationCycle, native_enum=False), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EnvironmentMetric(Base):
    __tablename__ = "environment_metrics"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True
    )
    metric_type: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- Compatibility Hiring (HR Workbook v6) ---


class AssessmentType(str, enum.Enum):
    quick_screen = "quick_screen"
    full_calibration = "full_calibration"


class OverallRisk(str, enum.Enum):
    green = "green"  # Recommended
    yellow = "yellow"  # Conditional
    red = "red"  # Tactical / high supervision


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    assessments: Mapped[list["CompatibilityAssessment"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    development_plans: Mapped[list["DevelopmentPlan"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )


class CompatibilityAssessment(Base):
    __tablename__ = "compatibility_assessments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type: Mapped[AssessmentType] = mapped_column(
        Enum(AssessmentType, native_enum=False), nullable=False
    )
    reviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    # Per-signal ratings: {signal_key: "low"|"medium"|"high"}.
    signals: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Full-calibration compatibility dimensions: {dimension_key: value}.
    dimensions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    overall_risk: Mapped[OverallRisk | None] = mapped_column(
        Enum(OverallRisk, native_enum=False), nullable=True
    )
    recommendation: Mapped[str | None] = mapped_column(String(500), nullable=True)
    action_items: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_of_evidence: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    candidate: Mapped["Candidate"] = relationship(back_populates="assessments")


class DevelopmentPlan(Base):
    __tablename__ = "development_plans"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True, nullable=False
    )
    risk_area: Mapped[str | None] = mapped_column(String(200), nullable=True)
    observed_pattern: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_support: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    progress_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    candidate: Mapped["Candidate"] = relationship(back_populates="development_plans")
