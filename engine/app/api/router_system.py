import logging
import os
import platform
import signal
import sys
import threading

from fastapi import APIRouter, HTTPException, Query

from app.core.database import get_duckdb_connection, get_sqlite_connection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/system", tags=["system"])


def _ok(data):
    return {"success": True, "data": data, "error": None}


def _err(code: str, detail: str, status: int = 400):
    raise HTTPException(
        status_code=status,
        detail={"success": False, "data": None, "error": {"code": code, "detail": detail}},
    )


@router.get("/info")
def system_info():
    try:
        conn_duck = get_duckdb_connection()
        duckdb_version = conn_duck.execute("SELECT library_version FROM pragma_version()").fetchone()[0]

        conn_sql = get_sqlite_connection()
        stores_count = conn_sql.execute(
            "SELECT COUNT(*) FROM stores",
        ).fetchone()[0]

        # Memory usage
        memory_mb = None
        try:
            import psutil
            memory_mb = round(psutil.Process().memory_info().rss / 1024 / 1024, 1)
        except ImportError:
            pass

        return _ok({
            "status": "ok",
            "python_version": sys.version.split()[0],
            "platform": platform.system(),
            "duckdb_version": duckdb_version,
            "stores_count": stores_count,
            "memory_usage_mb": memory_mb,
        })
    except Exception:
        logger.exception("System info failed")
        _err("SYSTEM_ERROR", "Failed to retrieve system info", 500)


@router.get("/tasks/{store_id}")
def get_tasks(store_id: str):
    try:
        conn = get_sqlite_connection()
        rows = conn.execute(
            """
            SELECT id, task_type, status, progress, error, created_at, updated_at
            FROM background_tasks
            WHERE store_id = ?
            ORDER BY created_at DESC
            LIMIT 50
            """,
            [store_id],
        ).fetchall()

        items = [
            {
                "id": r[0],
                "task_type": r[1],
                "status": r[2],
                "progress": r[3],
                "error": r[4],
                "created_at": r[5],
                "updated_at": r[6],
            }
            for r in rows
        ]

        return _ok({"items": items})
    except Exception:
        logger.exception("Failed to retrieve tasks")
        _err("SYSTEM_ERROR", "Failed to retrieve background tasks", 500)


@router.post("/shutdown")
def shutdown():
    """Graceful shutdown endpoint called by the Tauri shell on app close.

    Sends SIGINT to the current process so uvicorn triggers the FastAPI
    lifespan teardown (scheduler stop, DB close) before exiting.
    """
    logger.info("Shutdown requested via /system/shutdown")

    def _trigger():
        # Small delay so the HTTP response can be sent first
        import time
        time.sleep(0.3)
        os.kill(os.getpid(), signal.SIGINT)

    threading.Thread(target=_trigger, daemon=True).start()
    return _ok({"message": "Shutting down"})
