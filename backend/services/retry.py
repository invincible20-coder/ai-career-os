"""
Retry helpers for transient failures.
"""

from __future__ import annotations

import asyncio

import httpx
from sqlalchemy.exc import OperationalError

from backend.services.exceptions import ServiceError

_OPENAI_TRANSIENT_ERRORS: tuple[type[BaseException], ...] = ()

try:  # pragma: no cover - fallback only if dependency shape changes
    from openai import APIConnectionError, APITimeoutError, InternalServerError, RateLimitError
except ImportError:  # pragma: no cover
    pass
else:  # pragma: no cover - exercised only when specific OpenAI failures are raised
    _OPENAI_TRANSIENT_ERRORS = (
        APIConnectionError,
        APITimeoutError,
        InternalServerError,
        RateLimitError,
    )


def is_transient_error(exc: BaseException) -> bool:
    """Return True when the exception represents a retryable transient failure."""

    if isinstance(exc, ServiceError):
        return bool(exc.errors) and all(error.retryable for error in exc.errors)

    transient_types = (
        asyncio.TimeoutError,
        TimeoutError,
        httpx.TimeoutException,
        httpx.NetworkError,
        httpx.RemoteProtocolError,
        OperationalError,
        *_OPENAI_TRANSIENT_ERRORS,
    )
    return isinstance(exc, transient_types)


def backoff_seconds(
    attempt: int,
    *,
    base_delay: float,
    max_delay: float,
) -> float:
    """Return an exponential backoff delay bounded by `max_delay`."""

    scaled = base_delay * (2 ** max(attempt - 1, 0))
    return min(max_delay, scaled)
