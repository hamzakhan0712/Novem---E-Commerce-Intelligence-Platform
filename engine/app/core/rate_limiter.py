"""
Centralized rate-limiter configuration using slowapi.

Import `limiter` and `rate_limit_exceeded_handler` to wire into FastAPI,
or import `limiter` directly in routers for per-endpoint limits.

Default global limit: 120 requests/minute per client IP.
Expensive endpoints (ML, copilot, export) get tighter per-endpoint limits.
"""

from slowapi import Limiter, _rate_limit_exceeded_handler as _handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from starlette.responses import JSONResponse


def _key_func(request: Request) -> str:
    return get_remote_address(request) or "127.0.0.1"


limiter = Limiter(
    key_func=_key_func,
    default_limits=["120/minute"],
    storage_uri="memory://",
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return a structured JSON error matching the NOVEM API format."""
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "detail": f"Rate limit exceeded: {exc.detail}. Please slow down.",
            },
        },
    )
