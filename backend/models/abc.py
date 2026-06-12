"""
ABC adaptive recommendation models.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from backend.models.career import UserProfile
from backend.models.job import Job


class BehaviorEventType(str, Enum):
    """User actions that can teach the recommendation engine."""

    JOB_VIEWED = "job_viewed"
    JOB_CLICKED = "job_clicked"
    JOB_IGNORED = "job_ignored"
    JOB_SAVED = "job_saved"
    APPLICATION_STARTED = "application_started"
    APPLICATION_COMPLETED = "application_completed"
    APPLICATION_ABANDONED = "application_abandoned"
    RESUME_SELECTED = "resume_selected"
    COVER_LETTER_GENERATED = "cover_letter_generated"


class OutcomeType(str, Enum):
    """Consequences observed after a user acts."""

    NO_RESPONSE = "no_response"
    REJECTION = "rejection"
    ASSESSMENT = "assessment"
    INTERVIEW = "interview"
    FINAL_ROUND = "final_round"
    OFFER = "offer"
    ACCEPTED = "accepted"
    FOLLOW_UP_REQUESTED = "follow_up_requested"


class RecommendationEvent(BaseModel):
    """Antecedent record explaining why a job was recommended."""

    event_id: str
    event_type: str = "job_shown"
    user_id: str
    hunt_id: str
    job_id: str
    ranking_position: int
    base_match_score: float
    final_score: float
    recommendation_reason: str
    strategy_weights_used: dict[str, float] = Field(default_factory=dict)
    filters_applied: dict[str, Any] = Field(default_factory=dict)
    session_id: str
    job_category: str
    timestamp: datetime


class BehaviorEventCreate(BaseModel):
    """Request body for logging behavior tied to one recommendation context."""

    antecedent_event_id: str
    event_type: BehaviorEventType
    user_id: str | None = None
    hunt_id: str | None = None
    session_id: str | None = None
    job_id: str | None = None
    resume_id: str | None = None
    job_category: str | None = None


class BehaviorEvent(BaseModel):
    """Persisted behavior event."""

    event_id: str
    antecedent_event_id: str
    user_id: str
    hunt_id: str
    session_id: str
    event_type: BehaviorEventType
    job_id: str
    resume_id: str | None = None
    job_category: str
    timestamp: datetime


class OutcomeCreate(BaseModel):
    """Request body for logging a consequence of behavior."""

    behavior_event_id: str
    outcome_type: OutcomeType
    response_time_days: float = Field(ge=0)


class OutcomeEvent(BaseModel):
    """Persisted consequence event."""

    outcome_id: str
    behavior_event_id: str
    outcome_type: OutcomeType
    response_time_days: float
    timestamp: datetime


class CategoryStrategyStats(BaseModel):
    """Computed category-level learning signal."""

    applications_count: int = 0
    interviews_count: int = 0
    rejection_count: int = 0
    no_response_count: int = 0
    offers_count: int = 0
    follow_up_count: int = 0
    success_rate: float = 0.0
    avg_response_time: float = 0.0
    click_rate: float = 0.0
    application_rate: float = 0.0
    abandonment_rate: float = 0.0
    ignore_rate: float = 0.0
    resume_performance_score: float = 0.0
    recent_trend_score: float = 0.0
    score: float = 0.0
    weight: float = 0.5
    confidence: float = 0.0


class UserStrategyProfile(BaseModel):
    """Current learned strategy profile for one user."""

    user_id: str
    category_weights: dict[str, float] = Field(default_factory=dict)
    category_success_rates: dict[str, float] = Field(default_factory=dict)
    click_rates: dict[str, float] = Field(default_factory=dict)
    application_rates: dict[str, float] = Field(default_factory=dict)
    avg_response_times: dict[str, float] = Field(default_factory=dict)
    category_profiles: dict[str, CategoryStrategyStats] = Field(default_factory=dict)
    updated_at: datetime


class RankedJob(BaseModel):
    """A job after ABC-driven adaptive scoring."""

    job: Job
    event_id: str
    job_id: str
    rank: int
    job_category: str
    keyword_match: float
    skill_match: float
    education_match: float
    experience_match: float
    location_match: float
    base_match_score: float
    behavior_score: float
    outcome_score: float
    category_weight: float
    confidence: float
    confidence_percent: float
    uncertainty_percent: float
    evidence_strength: float
    exploration_bonus: float
    repetition_penalty: float
    final_score: float
    reason: str
    explanation: list[str] = Field(default_factory=list)
    signal_breakdown: dict[str, float] = Field(default_factory=dict)
    strategy_weights: dict[str, float] = Field(default_factory=dict)
    filters: dict[str, Any] = Field(default_factory=dict)
    # V2 Behavioral Intelligence fields
    semantic_score: float = 0.0
    pattern_score: float = 0.0
    temporal_score: float = 0.0
    memory_score: float = 0.0
    persona_alignment: float = 0.5


class RankJobsRequest(BaseModel):
    """API request for ranking supplied jobs through the ABC engine."""

    user_id: str
    goal: str
    jobs: list[Job]
    profile: UserProfile | None = None
    hunt_id: str | None = None
    session_id: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)


class RankJobsResponse(BaseModel):
    """API response containing explainable ranked recommendations."""

    user_id: str
    hunt_id: str
    session_id: str
    recommendations: list[RankedJob]
