import logging
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable

from app.core.database import get_sqlite_connection

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)
_tasks: dict[str, Future] = {}


def submit(task_type: str, dataset_id: str, fn: Callable, *args: Any) -> str:
    """Submit a background task. Returns the task_id."""
    task_id = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()

    conn = get_sqlite_connection()
    conn.execute(
        """
        INSERT INTO background_tasks (id, dataset_id, task_type, status, progress, created_at, updated_at)
        VALUES (?, ?, ?, 'pending', 0, ?, ?)
        """,
        [task_id, dataset_id, task_type, now, now],
    )
    conn.commit()

    def _wrapper():
        try:
            _update_status(task_id, "running", 0)
            result = fn(*args, progress_cb=lambda p: _update_status(task_id, "running", p))
            _update_status(task_id, "completed", 100)
            return result
        except Exception as exc:
            logger.exception("Background task %s failed", task_id)
            _update_status(task_id, "failed", -1, error=str(exc))
            raise

    future = _executor.submit(_wrapper)
    _tasks[task_id] = future
    logger.info("Submitted background task %s (%s) for dataset %s", task_id, task_type, dataset_id)
    return task_id


def get_status(task_id: str) -> dict | None:
    """Get the current status of a background task."""
    conn = get_sqlite_connection()
    row = conn.execute(
        "SELECT id, dataset_id, task_type, status, progress, error, created_at, updated_at FROM background_tasks WHERE id = ?",
        [task_id],
    ).fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "dataset_id": row[1],
        "task_type": row[2],
        "status": row[3],
        "progress": row[4],
        "error": row[5],
        "created_at": row[6],
        "updated_at": row[7],
    }


def get_tasks_for_dataset(dataset_id: str) -> list[dict]:
    """Get all tasks for a dataset, most recent first."""
    conn = get_sqlite_connection()
    rows = conn.execute(
        """
        SELECT id, dataset_id, task_type, status, progress, error, created_at, updated_at
        FROM background_tasks
        WHERE dataset_id = ?
        ORDER BY created_at DESC
        """,
        [dataset_id],
    ).fetchall()
    return [
        {
            "id": r[0],
            "dataset_id": r[1],
            "task_type": r[2],
            "status": r[3],
            "progress": r[4],
            "error": r[5],
            "created_at": r[6],
            "updated_at": r[7],
        }
        for r in rows
    ]


def _update_status(task_id: str, status: str, progress: int, error: str | None = None):
    """Persist task status to SQLite."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_sqlite_connection()
    conn.execute(
        "UPDATE background_tasks SET status = ?, progress = ?, error = ?, updated_at = ? WHERE id = ?",
        [status, progress, error, now, task_id],
    )
    conn.commit()
