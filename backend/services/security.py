"""
HTTP security middleware.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers and lightweight CSRF protection for cookie auth."""

    def __init__(self, app, *, csrf_enabled: bool = True) -> None:
        super().__init__(app)
        self.csrf_enabled = csrf_enabled

    async def dispatch(self, request: Request, call_next) -> Response:
        if self.csrf_enabled and self._requires_csrf(request):
            token_cookie = request.cookies.get("csrf_token")
            token_header = request.headers.get("x-csrf-token")
            if not token_cookie or token_cookie != token_header:
                return Response(
                    content='{"success":false,"data":null,"errors":[{"code":"csrf_failed","message":"CSRF token missing or invalid"}]}',
                    status_code=403,
                    media_type="application/json",
                )

        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; connect-src 'self' http://localhost:* ws://localhost:*; "
            "img-src 'self' data: https://fastapi.tiangolo.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
        )
        return response

    @staticmethod
    def _requires_csrf(request: Request) -> bool:
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return False
        if not request.cookies.get("access_token"):
            return False
        return request.url.path.startswith("/api/")
