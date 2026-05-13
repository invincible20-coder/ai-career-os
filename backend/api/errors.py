"""
Exception handlers that guarantee the standard response envelope.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.api.schemas import ResponseEnvelope
from backend.core.logger import get_logger
from backend.models.errors import ErrorDetail
from backend.services.exceptions import ServiceError

logger = get_logger(__name__)


def _response(status_code: int, *, errors: list[ErrorDetail]) -> JSONResponse:
    payload = ResponseEnvelope(success=False, data=None, errors=errors)
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach JSON error handlers to the app."""

    @app.exception_handler(ServiceError)
    async def _service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
        logger.warning(
            "service_error_response",
            extra={
                "event": "service_error_response",
                "path": str(request.url.path),
                "status_code": exc.status_code,
                "errors": [error.model_dump(mode="json") for error in exc.errors],
            },
        )
        return _response(exc.status_code, errors=exc.errors)

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        logger.warning(
            "request_validation_failed",
            extra={
                "event": "request_validation_failed",
                "path": str(request.url.path),
                "errors": exc.errors(),
            },
        )
        return _response(
            400,
            errors=[
                ErrorDetail(
                    code="invalid_request",
                    message="Request validation failed",
                    details={"issues": exc.errors()},
                )
            ],
        )

    @app.exception_handler(Exception)
    async def _unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unexpected_api_error",
            extra={"event": "unexpected_api_error", "path": str(request.url.path)},
        )
        return _response(
            500,
            errors=[
                ErrorDetail(
                    code="internal_server_error",
                    message="An unexpected error occurred",
                    details={"reason": str(exc)},
                )
            ],
        )
