"""
ABC Behavioral Intelligence Engine V2.0 — Domain Models.

This module defines the core data structures for the behavioral intelligence
engine, including the immutable learning event store, dual memory system,
behavioral pattern discovery, consequence weighting, career persona inference,
and self-evaluation metrics.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Phase 1 — Immutable ABC Learning Event
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ABCLearningEvent(BaseModel, frozen=True):
    """Immutable, append-only learning unit: Antecedent → Behavior → Consequence.

    Every recommendation, application, interview, rejection, and offer
    becomes a learning signal captured here. These events are the
    historical truth source — never edited, never deleted.
    """

    event_id: str
    user_id: str
    timestamp: datetime

    # Antecedent — the environmental conditions at recommendation time
    antecedent: AntecedentSnapshot

    # Behavior — the user action
    behavior: BehaviorSnapshot

    # Consequence — the observed outcome
    consequence: ConsequenceSnapshot

    # Engine state at time of event
    confidence_at_time: float = Field(ge=0, le=1)
    strategy_snapshot: dict[str, Any] = Field(default_factory=dict)


class AntecedentSnapshot(BaseModel, frozen=True):
    """Environmental conditions at the time a recommendation was generated."""

    job_id: str
    job_title: str
    job_company: str
    job_category: str
    job_location: str
    job_requirements: list[str] = Field(default_factory=list)
    goal: str = ""
    hunt_id: str = ""
    session_id: str = ""
    base_match_score: float = 0.0
    ranking_position: int = 0
    recommendation_reason: str = ""
    antecedent_signature: str = ""


class BehaviorSnapshot(BaseModel, frozen=True):
    """User action that was observed."""

    behavior_event_id: str
    event_type: str
    resume_id: str | None = None


class ConsequenceSnapshot(BaseModel, frozen=True):
    """Observed outcome after user action."""

    outcome_id: str | None = None
    outcome_type: str | None = None
    consequence_level: str = "unknown"
    consequence_weight: float = 0.0
    response_time_days: float = 0.0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Phase 6 — Consequence Weighting
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ConsequenceLevel(str, Enum):
    """10-level consequence hierarchy. Higher levels carry more learning weight."""

    IGNORED = "ignored"
    VIEWED = "viewed"
    CLICKED = "clicked"
    SAVED = "saved"
    APPLIED = "applied"
    ASSESSMENT = "assessment"
    INTERVIEW = "interview"
    FINAL_ROUND = "final_round"
    OFFER = "offer"
    ACCEPTED = "accepted"


# Numeric weight for each consequence level.
CONSEQUENCE_WEIGHTS: dict[str, float] = {
    ConsequenceLevel.IGNORED.value: 0.0,
    ConsequenceLevel.VIEWED.value: 0.05,
    ConsequenceLevel.CLICKED.value: 0.10,
    ConsequenceLevel.SAVED.value: 0.15,
    ConsequenceLevel.APPLIED.value: 0.25,
    ConsequenceLevel.ASSESSMENT.value: 0.40,
    ConsequenceLevel.INTERVIEW.value: 0.60,
    ConsequenceLevel.FINAL_ROUND.value: 0.75,
    ConsequenceLevel.OFFER.value: 0.90,
    ConsequenceLevel.ACCEPTED.value: 1.00,
}


def consequence_weight_for(level: str) -> float:
    """Look up the numeric weight for a consequence level string."""
    return CONSEQUENCE_WEIGHTS.get(level, 0.0)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Phase 2 — Dual Memory System
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class MemoryEntry(BaseModel):
    """Single memory item with a signal strength and last-seen timestamp."""

    key: str
    signal_strength: float = Field(ge=0, le=1, default=0.5)
    occurrence_count: int = 1
    last_seen: datetime
    category: str = "general"


class ShortTermMemory(BaseModel):
    """Fast-decaying memory tracking recent user context.

    Tracks: recent interests, recent searches, recent applications, recent goals.
    Half-life: 7 days.
    """

    user_id: str
    recent_interests: list[MemoryEntry] = Field(default_factory=list)
    recent_searches: list[MemoryEntry] = Field(default_factory=list)
    recent_applications: list[MemoryEntry] = Field(default_factory=list)
    recent_goals: list[MemoryEntry] = Field(default_factory=list)
    updated_at: datetime

    @property
    def half_life_days(self) -> float:
        return 7.0


class LongTermMemory(BaseModel):
    """Slow-decaying memory tracking stable user preferences.

    Tracks: stable preferences, successful career patterns, persistent skill interests.
    Half-life: 90 days.
    """

    user_id: str
    stable_preferences: list[MemoryEntry] = Field(default_factory=list)
    successful_patterns: list[MemoryEntry] = Field(default_factory=list)
    persistent_skills: list[MemoryEntry] = Field(default_factory=list)
    updated_at: datetime

    @property
    def half_life_days(self) -> float:
        return 90.0


class DualMemoryState(BaseModel):
    """Combined short-term + long-term memory for a user."""

    user_id: str
    short_term: ShortTermMemory
    long_term: LongTermMemory
    updated_at: datetime


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Phase 3 — Behavioral Pattern Discovery
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TrendDirection(str, Enum):
    """Direction of pattern evolution."""

    RISING = "rising"
    STABLE = "stable"
    FALLING = "falling"


class BehavioralPattern(BaseModel):
    """A discovered recurring behavioral pattern with outcome statistics.

    Example:
        Remote + Python + Startup
        Occurrences: 42, Interviews: 19, Offers: 5
        Confidence: 0.84, Trend: Rising
    """

    pattern_id: str
    user_id: str
    antecedent_signature: str
    antecedent_embedding: list[float] = Field(default_factory=list)
    occurrences: int = 0
    views: int = 0
    clicks: int = 0
    saves: int = 0
    applies: int = 0
    assessments: int = 0
    interviews: int = 0
    final_rounds: int = 0
    offers: int = 0
    rejections: int = 0
    acceptances: int = 0
    confidence_score: float = Field(ge=0, le=1, default=0.0)
    last_seen: datetime
    trend_direction: TrendDirection = TrendDirection.STABLE
    created_at: datetime


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Phase 10 — Career Persona Evolution
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class PersonaType(str, Enum):
    """Inferred career personas derived from ABC history."""

    EXPLORER = "explorer"
    BACKEND_BUILDER = "backend_builder"
    FRONTEND_CRAFTER = "frontend_crafter"
    AI_ENGINEER = "ai_engineer"
    ML_RESEARCHER = "ml_researcher"
    PLATFORM_ENGINEER = "platform_engineer"
    DATA_SPECIALIST = "data_specialist"
    MOBILE_DEVELOPER = "mobile_developer"
    PRODUCT_DESIGNER = "product_designer"
    TECH_LEADER = "tech_leader"
    GENERALIST = "generalist"


class CareerPersona(BaseModel):
    """Dynamically inferred career persona from behavioral history.

    The system infers the persona — it never asks the user.
    The persona continuously evolves as new outcomes arrive.
    """

    user_id: str
    primary_persona: PersonaType = PersonaType.EXPLORER
    secondary_persona: PersonaType | None = None
    persona_confidence: float = Field(ge=0, le=1, default=0.0)
    persona_scores: dict[str, float] = Field(default_factory=dict)
    evolution_history: list[PersonaSnapshot] = Field(default_factory=list)
    updated_at: datetime


class PersonaSnapshot(BaseModel):
    """Point-in-time persona capture for evolution tracking."""

    persona: PersonaType
    confidence: float = Field(ge=0, le=1)
    timestamp: datetime


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Phase 11 — Strategy Feedback Loop
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class StrategySignalType(str, Enum):
    """Types of strategy signals generated by the ABC engine."""

    RESUME_WEAKNESS = "resume_weakness"
    STRONG_FIT = "strong_fit"
    CATEGORY_MISMATCH = "category_mismatch"
    INCREASE_VOLUME = "increase_volume"
    NARROW_FOCUS = "narrow_focus"
    EXPLORE_ADJACENT = "explore_adjacent"
    IMPROVE_TARGETING = "improve_targeting"


class StrategyFeedbackSignal(BaseModel):
    """Signal from the ABC engine to the strategy engine."""

    signal_id: str
    user_id: str
    signal_type: StrategySignalType
    category: str
    strength: float = Field(ge=0, le=1)
    evidence: list[str] = Field(default_factory=list)
    recommended_action: str = ""
    created_at: datetime


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Phase 14 — Self-Evaluation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class SelfEvaluationMetrics(BaseModel):
    """Engine quality tracking — the system evaluates its own predictions."""

    user_id: str
    interview_conversion_rate: float = 0.0
    offer_conversion_rate: float = 0.0
    recommendation_acceptance_rate: float = 0.0
    pattern_accuracy: float = 0.0
    confidence_calibration: float = 0.0
    behavior_prediction_accuracy: float = 0.0
    total_predictions: int = 0
    correct_predictions: int = 0
    evaluation_window_days: int = 30
    updated_at: datetime


class PredictionRecord(BaseModel):
    """A tracked prediction for later evaluation."""

    prediction_id: str
    user_id: str
    predicted_outcome: str
    predicted_confidence: float = Field(ge=0, le=1)
    actual_outcome: str | None = None
    was_correct: bool | None = None
    job_id: str = ""
    category: str = ""
    created_at: datetime
    evaluated_at: datetime | None = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Phase 13 — ABC Analytics
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class PatternAnalytics(BaseModel):
    """Analytics for a single behavioral pattern."""

    pattern_id: str
    antecedent_signature: str
    occurrences: int
    success_rate: float
    confidence: float
    trend: TrendDirection


class ABCAnalyticsReport(BaseModel):
    """Full ABC analytics payload for the frontend."""

    user_id: str
    top_successful_patterns: list[PatternAnalytics] = Field(default_factory=list)
    pattern_confidence_distribution: dict[str, int] = Field(default_factory=dict)
    preference_evolution: list[dict[str, Any]] = Field(default_factory=list)
    persona_evolution: list[PersonaSnapshot] = Field(default_factory=list)
    behavior_trends: dict[str, TrendDirection] = Field(default_factory=dict)
    success_trajectory: list[dict[str, float]] = Field(default_factory=list)
    learning_velocity: float = 0.0
    self_evaluation: SelfEvaluationMetrics | None = None
    updated_at: datetime
