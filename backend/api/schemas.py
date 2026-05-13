"""
HTTP request and response schemas.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from backend.models.career import UserProfile
from backend.models.errors import ErrorDetail


class HuntRequest(UserProfile):
    """Incoming request body for a hunt."""

    goal: str | None = Field(None, min_length=2, max_length=500)


class CareerRecommendationRequest(UserProfile):
    """Incoming request body for direct career recommendations."""


class HealthPayload(BaseModel):
    """Health response payload."""

    status: str = "ok"
    version: str


class ResponseEnvelope(BaseModel):
    """Standard API response envelope."""

    success: bool
    data: Any | None = None
    errors: list[ErrorDetail] = Field(default_factory=list)
