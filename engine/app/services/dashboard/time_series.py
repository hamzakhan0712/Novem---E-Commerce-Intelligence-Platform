"""
Time-series generator — Produces metric trends at various granularities.
"""

import logging
from datetime import datetime, timedelta, timezone

from app.core.database import get_duckdb_connection

logger = logging.getLogger(__name__)

METRIC_SQL = {
    "revenue": "COALESCE(SUM(total_price - discount_amount), 0)",
    "orders": "COUNT(*)",
    "customers": "COUNT(DISTINCT customer_id)",
    "aov": "CASE WHEN COUNT(*) > 0 THEN SUM(total_price - discount_amount) / COUNT(*) ELSE 0 END",
}

GRANULARITY_TRUNC = {
    "daily": "day",
    "weekly": "week",
    "monthly": "month",
}


def get_time_series(
    store_id: str,
    metric: str = "revenue",
    granularity: str = "daily",
    period: str = "30d",
) -> list[dict]:
    """Return a list of {date, value} points for the given metric/granularity."""
    if metric not in METRIC_SQL:
        raise ValueError(f"Unknown metric: {metric}")
    if granularity not in GRANULARITY_TRUNC:
        raise ValueError(f"Unknown granularity: {granularity}")

    conn = get_duckdb_connection()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if period.endswith('m'):
        months = int(period[:-1])
        days = months * 30
    else:
        days = int(period.rstrip('d'))

    start = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0)
    trunc = GRANULARITY_TRUNC[granularity]
    agg = METRIC_SQL[metric]

    rows = conn.execute(
        f"""
        SELECT
            DATE_TRUNC('{trunc}', order_date::DATE) AS period_date,
            {agg} AS value
        FROM orders
        WHERE store_id = ?
          AND order_date >= ?
          AND status = 'completed'
        GROUP BY period_date
        ORDER BY period_date
        """,
        [store_id, start.isoformat()],
    ).fetchall()

    return [
        {"date": row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]), "value": round(float(row[1]), 2)}
        for row in rows
    ]
