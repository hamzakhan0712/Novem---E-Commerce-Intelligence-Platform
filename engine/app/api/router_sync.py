import json
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.database import get_sqlite_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sync"])


class CreateScheduleRequest(BaseModel):
    store_id: str
    connector_type: str
    data_types: list[str] = ["orders", "customers", "products"]
    interval_minutes: int = 60


@router.post("/schedule")
def create_or_update_schedule(req: CreateScheduleRequest):
    conn = get_sqlite_connection()
    store = conn.execute("SELECT id FROM stores WHERE id = ?", (req.store_id,)).fetchone()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    now = datetime.now().isoformat()
    data_types_json = json.dumps(req.data_types)

    existing = conn.execute(
        "SELECT id FROM sync_schedules WHERE store_id = ? AND connector_type = ?",
        (req.store_id, req.connector_type),
    ).fetchone()

    if existing:
        schedule_id = existing["id"]
        conn.execute(
            "UPDATE sync_schedules SET data_types = ?, interval_minutes = ?, is_active = 1, updated_at = ? WHERE id = ?",
            (data_types_json, req.interval_minutes, now, schedule_id),
        )
    else:
        schedule_id = uuid.uuid4().hex[:12]
        conn.execute(
            "INSERT INTO sync_schedules (id, store_id, connector_type, data_types, interval_minutes, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (schedule_id, req.store_id, req.connector_type, data_types_json, req.interval_minutes, now),
        )

    conn.commit()

    # Register with APScheduler
    from app.core.scheduler import get_scheduler, _run_scheduled_sync

    scheduler = get_scheduler()
    job_id = f"sync_{schedule_id}"
    scheduler.add_job(
        _run_scheduled_sync,
        "interval",
        minutes=req.interval_minutes,
        id=job_id,
        replace_existing=True,
        kwargs={
            "schedule_id": schedule_id,
            "store_id": req.store_id,
            "data_types": req.data_types,
        },
    )

    return {"success": True, "data": {"schedule_id": schedule_id, "interval_minutes": req.interval_minutes}}


@router.get("/schedules/{store_id}")
def get_schedules(store_id: str):
    conn = get_sqlite_connection()
    rows = conn.execute(
        "SELECT * FROM sync_schedules WHERE store_id = ? ORDER BY created_at DESC",
        (store_id,),
    ).fetchall()

    schedules = []
    for r in rows:
        s = dict(r)
        s["data_types"] = json.loads(s["data_types"])
        s["is_active"] = bool(s["is_active"])
        schedules.append(s)

    return {"success": True, "data": schedules}


@router.delete("/schedule/{schedule_id}")
def delete_schedule(schedule_id: str):
    conn = get_sqlite_connection()
    row = conn.execute("SELECT id FROM sync_schedules WHERE id = ?", (schedule_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Schedule not found")

    conn.execute("DELETE FROM sync_schedules WHERE id = ?", (schedule_id,))
    conn.commit()

    # Remove from APScheduler
    from app.core.scheduler import get_scheduler
    scheduler = get_scheduler()
    job_id = f"sync_{schedule_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    return {"success": True, "data": None}


@router.post("/trigger/{store_id}")
def trigger_manual_sync(store_id: str):
    """Trigger an immediate sync using the store's saved schedule config."""
    conn = get_sqlite_connection()
    schedule = conn.execute(
        "SELECT * FROM sync_schedules WHERE store_id = ? AND is_active = 1 LIMIT 1",
        (store_id,),
    ).fetchone()

    if not schedule:
        raise HTTPException(status_code=404, detail="No active schedule for this store")

    from app.services.sync.sync_runner import run_sync
    data_types = json.loads(schedule["data_types"])

    try:
        result = run_sync(store_id, data_types, schedule_id=schedule["id"])
        return {"success": True, "data": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/history/{store_id}")
def get_sync_history(store_id: str, limit: int = 20):
    """Return recent import history entries that came from API syncs."""
    conn = get_sqlite_connection()
    rows = conn.execute(
        "SELECT * FROM import_history WHERE store_id = ? AND source_type NOT IN ('file', 'google_sheets', 'sample') "
        "ORDER BY imported_at DESC LIMIT ?",
        (store_id, limit),
    ).fetchall()

    return {"success": True, "data": [dict(r) for r in rows]}
