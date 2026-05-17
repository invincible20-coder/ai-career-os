"""
SQLAlchemy ORM models for persisted hunt state.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base SQLAlchemy model."""


class HuntRecord(Base):
    __tablename__ = "hunts"
    __table_args__ = (
        Index("ix_hunts_status_updated", "status", "updated_at"),
    )

    hunt_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_key: Mapped[str] = mapped_column(String(255), default="anonymous", nullable=False, index=True)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    original_goal: Mapped[str | None] = mapped_column(Text)
    goal_was_recommended: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    career_recommendation_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PlanRecord(Base):
    __tablename__ = "plans"

    plan_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    hunt_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hunts.hunt_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    step_count: Mapped[int] = mapped_column(Integer, nullable=False)
    steps_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class JobRecord(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("hunt_id", "external_job_id", name="uq_jobs_hunt_external_job"),
        Index("ix_jobs_hunt_title", "hunt_id", "title"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    hunt_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hunts.hunt_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    external_job_id: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    requirements: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    salary_range: Mapped[str | None] = mapped_column(String(255))
    url: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(64), default="web_scraper", nullable=False)
    posted_date: Mapped[str | None] = mapped_column(String(64))
    rank_position: Mapped[int | None] = mapped_column(Integer)
    base_match_score: Mapped[float | None] = mapped_column(Float)
    final_score: Mapped[float | None] = mapped_column(Float)
    recommendation_reason: Mapped[str | None] = mapped_column(Text)
    recommendation_event_id: Mapped[str | None] = mapped_column(String(36), index=True)
    category: Mapped[str | None] = mapped_column(String(64), index=True)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class ApplicationRecord(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("hunt_id", "job_id", name="uq_applications_hunt_job"),
        Index("ix_applications_hunt_created", "hunt_id", "created_at"),
        Index("ix_applications_user_timestamp", "user_key", "timestamp_applied"),
        Index("ix_applications_user_status", "user_key", "application_status"),
    )

    application_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_key: Mapped[str] = mapped_column(String(255), default="anonymous", nullable=False, index=True)
    hunt_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hunts.hunt_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(128), default="unknown", nullable=False)
    resume_version: Mapped[str] = mapped_column(String(128), default="standard-v1", nullable=False)
    resume_fingerprint_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("resume_fingerprints.id", ondelete="SET NULL"),
        index=True,
    )
    timestamp_applied: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    application_status: Mapped[str] = mapped_column(
        String(32),
        default="no_response",
        nullable=False,
    )
    is_referral: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    resume_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    cover_letter_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BehaviorMetricSnapshotRecord(Base):
    __tablename__ = "behavior_metric_snapshots"
    __table_args__ = (
        Index("ix_behavior_snapshots_user_created", "user_key", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    classification: Mapped[str] = mapped_column(String(32), nullable=False)
    total_applications: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    analysis_window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_days: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    apps_per_day: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    success_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    platform_distribution: Mapped[dict[str, int]] = mapped_column(JSON, default=dict, nullable=False)
    role_distribution: Mapped[dict[str, int]] = mapped_column(JSON, default=dict, nullable=False)
    role_diversity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    resume_success_rate: Mapped[dict[str, float]] = mapped_column(JSON, default=dict, nullable=False)
    referral_ratio: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    minimum_data_threshold_met: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class RecommendationEventRecord(Base):
    __tablename__ = "recommendation_events"
    __table_args__ = (
        Index("ix_recommendation_events_user_created", "user_id", "created_at"),
        Index("ix_recommendation_events_hunt_rank", "hunt_id", "rank_position"),
        Index("ix_recommendation_events_user_job", "user_id", "job_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), default="job_shown", nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    hunt_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    job_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    rank_position: Mapped[int] = mapped_column(Integer, nullable=False)
    base_match_score: Mapped[float] = mapped_column(Float, nullable=False)
    final_score: Mapped[float] = mapped_column(Float, nullable=False)
    recommendation_reason: Mapped[str] = mapped_column(Text, nullable=False)
    strategy_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    filters_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class BehaviorEventRecord(Base):
    __tablename__ = "behavior_events"
    __table_args__ = (
        Index("ix_behavior_events_user_created", "user_id", "created_at"),
        Index("ix_behavior_events_antecedent", "antecedent_event_id"),
        Index("ix_behavior_events_user_category", "user_id", "category"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    antecedent_event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("recommendation_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    hunt_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    job_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    resume_id: Mapped[str | None] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class OutcomeRecord(Base):
    __tablename__ = "outcomes"
    __table_args__ = (
        Index("ix_outcomes_behavior_created", "behavior_event_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    behavior_event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("behavior_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    outcome_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    response_time_days: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class UserStrategyProfileRecord(Base):
    __tablename__ = "user_strategy_profiles"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    category_weights_json: Mapped[dict[str, float]] = mapped_column(JSON, default=dict, nullable=False)
    category_success_rates_json: Mapped[dict[str, float]] = mapped_column(JSON, default=dict, nullable=False)
    click_rates_json: Mapped[dict[str, float]] = mapped_column(JSON, default=dict, nullable=False)
    application_rates_json: Mapped[dict[str, float]] = mapped_column(JSON, default=dict, nullable=False)
    avg_response_times_json: Mapped[dict[str, float]] = mapped_column(JSON, default=dict, nullable=False)
    category_profiles_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class ConversationTurnRecord(Base):
    __tablename__ = "conversation_turns"
    __table_args__ = (
        Index("ix_conversation_turns_user_created", "user_id", "created_at"),
        Index("ix_conversation_turns_user_session", "user_id", "session_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_signals_json: Mapped[dict[str, float]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    category_preferences_json: Mapped[dict[str, float]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class UserIntelligenceProfileRecord(Base):
    __tablename__ = "user_intelligence_profiles"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    latest_intent_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    latest_discovery_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    latest_confidence_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    conversation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class ResumeFingerprintRecord(Base):
    __tablename__ = "resume_fingerprints"
    __table_args__ = (
        UniqueConstraint("user_id", "content_hash", name="uq_resume_fingerprints_user_hash"),
        Index("ix_resume_fingerprints_user_resume", "user_id", "resume_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    resume_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    resume_version: Mapped[str] = mapped_column(String(128), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    features_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class ResumeCorrelationProfileRecord(Base):
    __tablename__ = "resume_correlation_profiles"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    feature_correlations_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    resume_effectiveness_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    total_linked_outcomes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class PredictiveCareerProfileRecord(Base):
    __tablename__ = "predictive_career_profiles"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_vector_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    predictions_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class StepExecutionRecord(Base):
    __tablename__ = "step_executions"
    __table_args__ = (
        UniqueConstraint("hunt_id", "step_name", name="uq_step_executions_hunt_step"),
        Index("ix_step_executions_hunt_status", "hunt_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hunt_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hunts.hunt_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_name: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    last_error_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class RateLimitRecord(Base):
    __tablename__ = "rate_limits"
    __table_args__ = (
        UniqueConstraint(
            "client_key",
            "route_key",
            "window_started_at",
            name="uq_rate_limits_client_route_window",
        ),
        Index("ix_rate_limits_client_route", "client_key", "route_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_key: Mapped[str] = mapped_column(String(255), nullable=False)
    route_key: Mapped[str] = mapped_column(String(128), nullable=False)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
