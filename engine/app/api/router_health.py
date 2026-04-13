import logging
import time

from fastapi import APIRouter

router = APIRouter()
logger = logging.getLogger(__name__)

_start_time = time.time()


@router.get("/health")
async def health_check():
    engine_ready = True
    status = "ok"

    try:
        from app.core.database import get_sqlite_connection
        get_sqlite_connection().execute("SELECT 1")
    except Exception:
        engine_ready = False
        status = "degraded"
        logger.warning("Health check: database connection failed")

    return {
        "success": True,
        "data": {
            "status": status,
            "uptime": round(time.time() - _start_time, 1),
            "api_version": "0.1.0",
            "engine_ready": engine_ready,
        },
        "error": None,
    }
