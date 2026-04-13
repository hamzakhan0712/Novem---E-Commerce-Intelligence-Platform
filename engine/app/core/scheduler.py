import logging

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(
            job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 300},
        )
    return _scheduler


def start_scheduler() -> None:
    scheduler = get_scheduler()
    if not scheduler.running:
        _restore_saved_schedules()
        _register_alert_check_job()
        scheduler.start()
        logger.info("APScheduler started")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")
    _scheduler = None


def _restore_saved_schedules() -> None:
    """On startup, re-register all active sync schedules from SQLite."""
    from app.core.database import get_sqlite_connection

    conn = get_sqlite_connection()
    rows = conn.execute(
        "SELECT id, store_id, connector_type, data_types, interval_minutes "
        "FROM sync_schedules WHERE is_active = 1"
    ).fetchall()

    import json
    scheduler = get_scheduler()

    for row in rows:
        job_id = f"sync_{row['id']}"
        data_types = json.loads(row["data_types"])

        scheduler.add_job(
            _run_scheduled_sync,
            "interval",
            minutes=row["interval_minutes"],
            id=job_id,
            replace_existing=True,
            kwargs={
                "schedule_id": row["id"],
                "store_id": row["store_id"],
                "data_types": data_types,
            },
        )
        logger.info(
            "Restored schedule %s for store %s (every %d min)",
            row["id"],
            row["store_id"],
            row["interval_minutes"],
        )


def _run_scheduled_sync(schedule_id: str, store_id: str, data_types: list[str]) -> None:
    """Callback executed by APScheduler for each sync interval."""
    from app.services.sync.sync_runner import run_sync

    logger.info("Scheduled sync triggered: schedule=%s store=%s", schedule_id, store_id)
    try:
        run_sync(store_id, data_types, schedule_id=schedule_id)
    except Exception as exc:
        logger.error("Scheduled sync failed for %s: %s", store_id, exc)

_ALERT_CHECK_JOB_ID = "background_alert_check"
_DEFAULT_ALERT_INTERVAL_HOURS = 6


def _register_alert_check_job() -> None:
    """Register a periodic job that checks KPI thresholds for all active stores."""
    import json
    from app.core.database import get_sqlite_connection

    scheduler = get_scheduler()

    conn = get_sqlite_connection()
    row = conn.execute(
        "SELECT value FROM settings WHERE key = ?", ("alert_check_interval_hours",)
    ).fetchone()
    interval_hours = _DEFAULT_ALERT_INTERVAL_HOURS
    if row:
        try:
            interval_hours = int(json.loads(row["value"]))
        except (ValueError, TypeError):
            pass

    scheduler.add_job(
        _run_alert_checks,
        "interval",
        hours=interval_hours,
        id=_ALERT_CHECK_JOB_ID,
        replace_existing=True,
    )
    logger.info("Alert check job registered (every %d hours)", interval_hours)


def _run_alert_checks() -> None:
    """Check KPI thresholds for every active store."""
    from app.core.database import get_sqlite_connection
    from app.services.alerts.alert_service import check_kpi_thresholds

    conn = get_sqlite_connection()
    rows = conn.execute("SELECT id FROM stores WHERE is_active = 1").fetchall()

    for row in rows:
        store_id = row["id"]
        try:
            alerts = check_kpi_thresholds(store_id)
            if alerts:
                logger.info(
                    "Alert check for store %s: %d alert(s) created",
                    store_id,
                    len(alerts),
                )
        except Exception as exc:
            logger.error("Alert check failed for store %s: %s", store_id, exc)