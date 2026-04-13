import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router_alerts import router as alerts_router
from app.api.router_auth import router as auth_router
from app.api.router_benchmarks import router as benchmarks_router
from app.api.router_connectors import router as connectors_router
from app.api.router_copilot import router as copilot_router
from app.api.router_credentials import router as credentials_router
from app.api.router_customers import router as customers_router
from app.api.router_dashboard import router as dashboard_router
from app.api.router_data_viewer import router as data_viewer_router
from app.api.router_email import router as email_router
from app.api.router_export import router as export_router
from app.api.router_forecasting import router as forecasting_router
from app.api.router_health import router as health_router
from app.api.router_ingestion import router as ingestion_router
from app.api.router_insights import router as insights_router
from app.api.router_marketing import router as marketing_router
from app.api.router_products import router as products_router
from app.api.router_sentiment import router as sentiment_router
from app.api.router_settings import router as settings_router
from app.api.router_stores import router as stores_router
from app.api.router_sync import router as sync_router
from app.api.router_system import router as system_router
from app.api.router_webhooks import router as webhooks_router
from app.config import CORS_ORIGINS
from app.core.database import (
    close_connections,
    init_duckdb_schema,
    init_sqlite_schema,
    run_integrity_checks,
    get_sqlite_connection,
)
from app.core.logging_config import setup_logging
from app.core.middleware import AuthMiddleware, RequestIdMiddleware, RequestLoggingMiddleware
from app.core.rate_limiter import limiter, rate_limit_exceeded_handler
from app.core.scheduler import start_scheduler, stop_scheduler
from slowapi.errors import RateLimitExceeded

setup_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("NOVEM compute engine starting...")
    run_integrity_checks()
    init_duckdb_schema()
    init_sqlite_schema()
    logger.info("Database schemas initialized")

    # Clear stale auth sessions on engine start.
    # This enforces the "every_start" password policy: when the Tauri app
    # (and its embedded engine) restarts, old sessions become invalid,
    # requiring the user to log in again.
    try:
        conn = get_sqlite_connection()
        conn.execute("DELETE FROM sessions")
        conn.commit()
        logger.info("Cleared stale auth sessions")
    except Exception:
        logger.debug("Could not clear sessions table (may not exist yet)")

    start_scheduler()
    yield
    logger.info("NOVEM compute engine shutting down...")
    stop_scheduler()
    close_connections()


app = FastAPI(
    title="NOVEM Compute Engine",
    version="0.3.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(AuthMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler so unhandled exceptions still return structured
    JSON with CORS headers (CORSMiddleware wraps this response)."""
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "data": None,
            "error": {"code": "INTERNAL_ERROR", "detail": "An internal error occurred. Check engine logs for details."},
        },
    )

app.include_router(auth_router)
app.include_router(health_router)
app.include_router(dashboard_router)
app.include_router(customers_router)
app.include_router(products_router)
app.include_router(marketing_router)
app.include_router(stores_router)
app.include_router(settings_router)
app.include_router(ingestion_router)
app.include_router(system_router)
app.include_router(alerts_router)
app.include_router(benchmarks_router)
app.include_router(export_router)
app.include_router(insights_router)
app.include_router(forecasting_router)
app.include_router(sentiment_router)
app.include_router(copilot_router)
app.include_router(credentials_router)
app.include_router(connectors_router)
app.include_router(webhooks_router)
app.include_router(sync_router)
app.include_router(data_viewer_router)
app.include_router(email_router)
