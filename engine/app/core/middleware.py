import logging
import time
import uuid
from functools import wraps
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

# Paths that do NOT require authentication
_PUBLIC_PREFIXES = ("/health", "/auth/", "/webhooks/")


class AuthMiddleware(BaseHTTPMiddleware):
    """Rejects requests without a valid session token (except public routes)."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        if any(path.startswith(p) for p in _PUBLIC_PREFIXES):
            return await call_next(request)

        if request.method == "OPTIONS":
            return await call_next(request)

        token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if not token:
            return JSONResponse(
                status_code=401,
                content={"success": False, "data": None, "error": {"code": "UNAUTHORIZED", "detail": "Authentication required"}},
            )

        from app.core.database import get_sqlite_connection
        conn = get_sqlite_connection()
        row = conn.execute("SELECT token FROM sessions WHERE token = ?", (token,)).fetchone()
        if not row:
            return JSONResponse(
                status_code=401,
                content={"success": False, "data": None, "error": {"code": "UNAUTHORIZED", "detail": "Invalid or expired session"}},
            )

        return await call_next(request)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assigns a short UUID to every request for tracing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = uuid.uuid4().hex[:8]
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        response.headers["X-NOVEM-API-Version"] = "1"
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs method, path, status code, and duration for every request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        log_level = logging.WARNING if duration_ms > 5000 else logging.INFO
        request_id = getattr(request.state, "request_id", "-")
        logger.log(
            log_level,
            "[%s] %s %s → %s (%.0fms)",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response


def timed(func: Callable) -> Callable:
    """Decorator that logs function execution time. WARNING if > 5s."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed_ms = (time.perf_counter() - start) * 1000
        level = logging.WARNING if elapsed_ms > 5000 else logging.DEBUG
        logging.getLogger(func.__module__).log(
            level,
            "%s completed in %.0fms",
            func.__qualname__,
            elapsed_ms,
        )
        return result

    return wrapper
