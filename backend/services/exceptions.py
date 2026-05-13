"""
Domain exceptions with HTTP-aware metadata.
"""

from __future__ import annotations

from typing import Iterable

from backend.models.errors import ErrorDetail


class ServiceError(Exception):
    """Base exception that carries structured errors."""

    status_code = 500

    def __init__(self, message: str, *, errors: Iterable[ErrorDetail]) -> None:
        super().__init__(message)
        self.errors = list(errors)


class PlanValidationError(ServiceError):
    """Raised when the planner produces an invalid workflow."""

    status_code = 400


class BadRequestError(ServiceError):
    """Raised when request input is incomplete or invalid for business rules."""

    status_code = 400


class NotFoundError(ServiceError):
    """Raised when a resource cannot be located."""

    status_code = 404


class TooManyRequestsError(ServiceError):
    """Raised when a caller exceeds the hunt rate limit."""

    status_code = 429


class PipelineExecutionError(ServiceError):
    """Raised when a pipeline step fails critically."""

    status_code = 500


class StepExecutionError(PipelineExecutionError):
    """Raised for step-specific execution failures."""
