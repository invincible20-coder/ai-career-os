"""
Models for the connected adaptive intelligence layer.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from backend.models.career import UserProfile


class ConversationIntentRequest(BaseModel):
    """Incoming user message that should update remembered intent."""

    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None
    profile: UserProfile | None = None


class ConversationalIntent(BaseModel):
    """Rolling interpretation of a user's evolving intent."""

    career_clarity: float = Field(ge=0, le=1)
    technical_interest: float = Field(ge=0, le=1)
    urgency: float = Field(ge=0, le=1)
    uncertainty: float = Field(ge=0, le=1)
    frustration: float = Field(ge=0, le=1)
    curiosity: float = Field(ge=0, le=1)
    commitment_level: float = Field(ge=0, le=1)
    exploration_mode: bool
    category_preferences: dict[str, float] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    updated_at: datetime


class ConversationTurn(BaseModel):
    """Persisted conversational evidence used by the intent engine."""

    turn_id: str
    user_id: str
    session_id: str
    message: str
    extracted_signals: dict[str, float] = Field(default_factory=dict)
    category_preferences: dict[str, float] = Field(default_factory=dict)
    created_at: datetime


class CareerPathSuggestion(BaseModel):
    """One ambiguity-preserving career hypothesis."""

    role: str
    category: str
    score: float = Field(ge=0, le=1)
    reason: str


class CareerDiscoveryResult(BaseModel):
    """Exploratory career view derived from mixed behavioral signals."""

    career_paths: list[CareerPathSuggestion] = Field(default_factory=list)
    ambiguity_score: float = Field(ge=0, le=1)
    exploration_mode: bool
    reasons: list[str] = Field(default_factory=list)
    updated_at: datetime


class ConfidenceEstimate(BaseModel):
    """Confidence in how strongly the system should exploit learned signals."""

    recommended_role: str | None = None
    confidence: float = Field(ge=0, le=1)
    profile_completeness: float = Field(ge=0, le=1)
    behavioral_consistency: float = Field(ge=0, le=1)
    outcome_reliability: float = Field(ge=0, le=1)
    data_volume_score: float = Field(ge=0, le=1)
    exploration_mode: bool
    ranking_aggressiveness: float = Field(ge=0, le=1)
    confidence_reason: list[str] = Field(default_factory=list)
    updated_at: datetime


class UserIntelligenceState(BaseModel):
    """Persisted connected state for one adaptive user profile."""

    user_id: str
    intent: ConversationalIntent
    discovery: CareerDiscoveryResult
    confidence: ConfidenceEstimate
    conversation_count: int = 0
    updated_at: datetime
