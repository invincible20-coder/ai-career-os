"""
Structured error models shared across the API and services.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """A single structured error entry."""

    code: str
    message: str
    hunt_id: str | None = None
    step: str | None = None
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)
