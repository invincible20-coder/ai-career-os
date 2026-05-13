"""
Hunt lifecycle models.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from backend.models.errors import ErrorDetail
from backend.models.application import Application, TrackerEntry
from backend.models.career import CareerRecommendation
from backend.models.job import Job
from backend.models.plan import ExecutionPlan, StepType


class HuntStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StepProgressStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StepProgress(BaseModel):
    """Persisted progress details for one orchestration step."""

    step: StepType
    status: StepProgressStatus
    attempt_count: int = 0
    idempotency_key: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime
    latency_ms: int | None = None
    last_errors: list[ErrorDetail] = Field(default_factory=list)


class HuntResult(BaseModel):
    """API-facing snapshot of a hunt."""

    hunt_id: str
    goal: str
    original_goal: str | None = None
    career_recommendation: CareerRecommendation | None = None
    goal_was_recommended: bool = False
    status: HuntStatus
    plan: ExecutionPlan | None = None
    jobs_found: list[Job] = Field(default_factory=list)
    applications: list[Application] = Field(default_factory=list)
    tracker: list[TrackerEntry] = Field(default_factory=list)
    progress: list[StepProgress] = Field(default_factory=list)
    errors: list[ErrorDetail] = Field(default_factory=list)
    created_at: datetime
    completed_at: datetime | None = None
    summary: dict[str, int] = Field(default_factory=dict)
