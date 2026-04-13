"""
KPI calculator — Computes core e-commerce metrics from DuckDB.
"""

import logging
from datetime import datetime, timedelta, timezone

from app.core.database import get_duckdb_connection

logger = logging.getLogger(__name__)


VALID_PERIODS = {"7d", "14d", "30d", "60d", "90d", "6m", "12m"}


def _parse_period(period: str) -> tuple[datetime, datetime, datetime, datetime]:
    """Parse a period string like '7d', '30d', '90d', '12m' into
    (current_start, current_end, prev_start, prev_end) datetimes."""
    if period not in VALID_PERIODS:
        period = "30d"

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if period.endswith('m'):
        months = int(period[:-1])
        days = months * 30
    else:
        days = int(period.rstrip('d'))

    current_end = now.replace(hour=23, minute=59, second=59)
    current_start = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0)
    prev_end = current_start - timedelta(seconds=1)
    prev_start = (current_start - timedelta(days=days)).replace(hour=0, minute=0, second=0)

    return current_start, current_end, prev_start, prev_end


def calculate_kpis(store_id: str, period: str = "30d") -> dict:
    """Calculate core KPIs: revenue, order count, unique customers, AOV.

    Returns current values + previous period values for comparison.
    """
    conn = get_duckdb_connection()
    current_start, current_end, prev_start, prev_end = _parse_period(period)

    def _query_period(start: datetime, end: datetime) -> dict:
        result = conn.execute(
            """
            SELECT
                COALESCE(SUM(total_price - discount_amount), 0) AS revenue,
                COUNT(*) AS order_count,
                COUNT(DISTINCT customer_id) AS unique_customers
            FROM orders
            WHERE store_id = ?
              AND order_date >= ?
              AND order_date <= ?
              AND status = 'completed'
            """,
            [store_id, start.isoformat(), end.isoformat()],
        ).fetchone()

        if not result:
            return {"revenue": 0.0, "order_count": 0, "unique_customers": 0, "aov": 0.0}

        revenue = float(result[0])
        order_count = int(result[1])
        unique_customers = int(result[2])
        aov = revenue / order_count if order_count > 0 else 0.0

        return {
            "revenue": round(revenue, 2),
            "order_count": order_count,
            "unique_customers": unique_customers,
            "aov": round(aov, 2),
        }

    current = _query_period(current_start, current_end)
    previous = _query_period(prev_start, prev_end)

    def _change_pct(curr: float, prev: float) -> float:
        if prev == 0:
            return 0.0 if curr == 0 else 100.0
        return round(((curr - prev) / prev) * 100, 1)

    return {
        "period": period,
        "current": current,
        "previous": previous,
        "changes": {
            "revenue": _change_pct(current["revenue"], previous["revenue"]),
            "order_count": _change_pct(current["order_count"], previous["order_count"]),
            "unique_customers": _change_pct(current["unique_customers"], previous["unique_customers"]),
            "aov": _change_pct(current["aov"], previous["aov"]),
        },
    }
