"""
Behavior analytics and adaptive strategy models.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ApplicationOutcomeStatus(str, Enum):
    """Outcome status used for behavior analytics."""

    NO_RESPONSE = "no_response"
    REJECTED = "rejected"
    INTERVIEW = "interview"
    OFFER = "offer"


class BehaviorType(str, Enum):
    """Deterministic behavior classes derived from application history."""

    INSUFFICIENT_DATA = "insufficient_data"
    HARDCORE = "hardcore"
    MASS_APPLIER = "mass_applier"
    PASSIVE = "passive"
    DESPERATE = "desperate"
    NETWORKER = "networker"


class BehaviorMetrics(BaseModel):
    """Derived metrics used by the classifier and strategy engine."""

    user_key: str
    total_applications: int = 0
    analysis_window_days: int = 30
    observed_days: float = 0
    apps_per_day: float = 0
    success_rate: float = 0
    platform_distribution: dict[str, int] = Field(default_factory=dict)
    role_diversity: int = 0
    role_distribution: dict[str, int] = Field(default_factory=dict)
    resume_success_rate: dict[str, float] = Field(default_factory=dict)
    referral_ratio: float = 0
    minimum_data_threshold_met: bool = False
    computed_at: datetime | None = None


class BehaviorProfile(BaseModel):
    """Current behavior classification with the metrics behind it."""

    user_key: str
    classification: BehaviorType
    metrics: BehaviorMetrics
    explanation: str
    updated_at: datetime


class StrategyAdjustment(BaseModel):
    """Job hunt strategy knobs chosen from the current behavior profile."""

    user_key: str
    behavior_type: BehaviorType
    max_applications: int
    min_fit_score: float
    resume_customization_depth: str
    preferred_platforms: list[str] = Field(default_factory=list)
    role_similarity_required: bool = False
    prioritize_referrals: bool = False
    application_frequency: str = "steady"
    networking_suggestions: list[str] = Field(default_factory=list)
    explanation: str
    updated_at: datetime


class AnalyticsReport(BaseModel):
    """API-facing analytics report for a user."""

    user_key: str
    metrics: BehaviorMetrics
    classification: BehaviorType
    top_platforms: list[dict[str, Any]] = Field(default_factory=list)
    top_roles: list[dict[str, Any]] = Field(default_factory=list)
    best_resume_versions: list[dict[str, Any]] = Field(default_factory=list)
    generated_at: datetime
