import logging
import uuid
from datetime import datetime, timezone

from app.core.database import get_sqlite_connection
from app.models.alerts import AlertOut

logger = logging.getLogger(__name__)


def create_alert(
    store_id: str | None,
    module: str,
    severity: str,
    title: str,
    message: str,
) -> AlertOut:
    conn = get_sqlite_connection()
    alert_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    conn.execute(
        """INSERT INTO alerts (id, store_id, module, severity, title, message, is_read, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 0, ?)""",
        (alert_id, store_id, module, severity, title, message, now),
    )
    conn.commit()

    return AlertOut(
        id=alert_id,
        store_id=store_id,
        module=module,
        severity=severity,
        title=title,
        message=message,
        is_read=False,
        created_at=now,
    )


def get_alerts(
    store_id: str | None = None,
    is_read: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[AlertOut], int]:
    conn = get_sqlite_connection()

    where_clauses: list[str] = []
    params: list[object] = []

    if store_id is not None:
        where_clauses.append("store_id = ?")
        params.append(store_id)
    if is_read is not None:
        where_clauses.append("is_read = ?")
        params.append(1 if is_read else 0)

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    count_row = conn.execute(
        f"SELECT COUNT(*) FROM alerts {where_sql}", params
    ).fetchone()
    total = count_row[0] if count_row else 0

    rows = conn.execute(
        f"""SELECT id, store_id, module, severity, title, message, is_read, created_at
            FROM alerts {where_sql}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?""",
        [*params, limit, offset],
    ).fetchall()

    alerts = [
        AlertOut(
            id=row["id"],
            store_id=row["store_id"],
            module=row["module"],
            severity=row["severity"],
            title=row["title"],
            message=row["message"],
            is_read=bool(row["is_read"]),
            created_at=row["created_at"],
        )
        for row in rows
    ]

    return alerts, total


def get_unread_count(store_id: str | None = None) -> int:
    conn = get_sqlite_connection()
    if store_id:
        row = conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE store_id = ? AND is_read = 0",
            (store_id,),
        ).fetchone()
    else:
        row = conn.execute("SELECT COUNT(*) FROM alerts WHERE is_read = 0").fetchone()
    return row[0] if row else 0


def mark_alerts_read(alert_ids: list[str]) -> int:
    if not alert_ids:
        return 0
    conn = get_sqlite_connection()
    placeholders = ",".join("?" for _ in alert_ids)
    cursor = conn.execute(
        f"UPDATE alerts SET is_read = 1 WHERE id IN ({placeholders})",
        alert_ids,
    )
    conn.commit()
    return cursor.rowcount


def mark_all_read(store_id: str | None = None) -> int:
    conn = get_sqlite_connection()
    if store_id:
        cursor = conn.execute(
            "UPDATE alerts SET is_read = 1 WHERE store_id = ? AND is_read = 0",
            (store_id,),
        )
    else:
        cursor = conn.execute("UPDATE alerts SET is_read = 1 WHERE is_read = 0")
    conn.commit()
    return cursor.rowcount


def delete_alert(alert_id: str) -> bool:
    conn = get_sqlite_connection()
    cursor = conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
    conn.commit()
    return cursor.rowcount > 0


def _get_alert_thresholds() -> dict:
    """Read user-configurable alert thresholds from settings, with defaults."""
    import json
    from app.core.database import get_sqlite_connection

    defaults = {
        "revenue_drop_pct": -20,
        "order_drop_pct": -25,
        "customer_drop_pct": -30,
        "aov_spike_pct": 50,
    }
    conn = get_sqlite_connection()
    row = conn.execute(
        "SELECT value FROM settings WHERE key = ?", ("alert_thresholds",)
    ).fetchone()
    if row:
        try:
            saved = json.loads(row["value"])
            defaults.update({k: v for k, v in saved.items() if k in defaults})
        except (ValueError, TypeError):
            pass
    return defaults


def check_kpi_thresholds(store_id: str) -> list[AlertOut]:
    """Check KPIs and generate alerts for anomalies."""
    from app.services.dashboard.kpi_calculator import calculate_kpis

    alerts_created: list[AlertOut] = []
    kpis = calculate_kpis(store_id, "30d")

    changes = kpis.get("changes", {})
    thresholds = _get_alert_thresholds()

    # Revenue drop alert
    revenue_change = changes.get("revenue", 0)
    if revenue_change is not None and revenue_change < thresholds["revenue_drop_pct"]:
        alerts_created.append(create_alert(
            store_id=store_id,
            module="dashboard",
            severity="warning",
            title="Revenue Drop Detected",
            message=f"Revenue has decreased by {abs(revenue_change):.1f}% compared to the previous period.",
        ))

    # Order count drop
    order_change = changes.get("order_count", 0)
    if order_change is not None and order_change < thresholds["order_drop_pct"]:
        alerts_created.append(create_alert(
            store_id=store_id,
            module="dashboard",
            severity="warning",
            title="Order Volume Decline",
            message=f"Order count has decreased by {abs(order_change):.1f}% compared to the previous period.",
        ))

    # Customer drop
    customer_change = changes.get("unique_customers", 0)
    if customer_change is not None and customer_change < thresholds["customer_drop_pct"]:
        alerts_created.append(create_alert(
            store_id=store_id,
            module="customers",
            severity="info",
            title="Customer Activity Decline",
            message=f"Unique customers decreased by {abs(customer_change):.1f}% compared to the previous period.",
        ))

    # AOV spike (unusually high might indicate data issue)
    aov_change = changes.get("aov", 0)
    if aov_change is not None and aov_change > thresholds["aov_spike_pct"]:
        alerts_created.append(create_alert(
            store_id=store_id,
            module="dashboard",
            severity="info",
            title="Unusual AOV Increase",
            message=f"Average order value increased by {aov_change:.1f}%. This may indicate a data anomaly or bulk orders.",
        ))

    return alerts_created
