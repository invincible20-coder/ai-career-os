"""
Execution plan models.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StepType(str, Enum):
    PLAN = "plan"
    SEARCH = "search"
    APPLY = "apply"
    TRACK = "track"


EXPECTED_STEP_ORDER: tuple[StepType, ...] = (
    StepType.PLAN,
    StepType.SEARCH,
    StepType.APPLY,
    StepType.TRACK,
)


class PlanStep(BaseModel):
    """A single plan step."""

    step_number: int = Field(..., ge=1)
    step_type: StepType
    description: str = Field(..., min_length=3, max_length=500)
    parameters: dict[str, Any] = Field(default_factory=dict)


class ExecutionPlan(BaseModel):
    """Validated plan returned by the planner agent."""

    goal: str
    summary: str = ""
    steps: list[PlanStep] = Field(default_factory=list)
