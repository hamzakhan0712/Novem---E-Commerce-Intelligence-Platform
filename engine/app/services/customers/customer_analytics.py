"""
Customer analytics — Computes customer metrics from DuckDB orders + customers tables.
"""

import logging
from datetime import datetime, timedelta, timezone

from app.core.database import get_duckdb_connection

logger = logging.getLogger(__name__)


def _parse_period(period: str) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if period.endswith('m'):
        months = int(period[:-1])
        days = months * 30
    else:
        days = int(period.rstrip('d'))
    start = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0)
    end = now.replace(hour=23, minute=59, second=59)
    return start, end


def _parse_period_with_prev(period: str) -> tuple[datetime, datetime, datetime, datetime]:
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


def _query_customer_metrics(conn, store_id: str, start: datetime, end: datetime) -> dict:
    """Compute customer metrics for a single period."""
    row = conn.execute(
        """
        SELECT
            COUNT(DISTINCT customer_id) AS total_customers,
            COUNT(DISTINCT CASE WHEN order_count = 1 THEN customer_id END) AS one_time,
            COUNT(DISTINCT CASE WHEN order_count > 1 THEN customer_id END) AS returning
        FROM (
            SELECT customer_id, COUNT(*) AS order_count
            FROM orders
            WHERE store_id = ?
              AND order_date >= ?
              AND order_date <= ?
              AND status = 'completed'
            GROUP BY customer_id
        )
        """,
        [store_id, start.isoformat(), end.isoformat()],
    ).fetchone()

    if not row or int(row[0]) == 0:
        return {
            "total_customers": 0,
            "one_time_customers": 0,
            "returning_customers": 0,
            "returning_rate": 0.0,
            "total_spend": 0.0,
            "avg_lifetime_value": 0.0,
        }

    total = int(row[0])
    one_time = int(row[1])
    returning = int(row[2])

    spend_row = conn.execute(
        """
        SELECT
            COALESCE(SUM(customer_total), 0) AS total_spend,
            COALESCE(AVG(customer_total), 0) AS avg_lifetime_value
        FROM (
            SELECT customer_id, SUM(total_price - discount_amount) AS customer_total
            FROM orders
            WHERE store_id = ?
              AND order_date >= ?
              AND order_date <= ?
              AND status = 'completed'
            GROUP BY customer_id
        )
        """,
        [store_id, start.isoformat(), end.isoformat()],
    ).fetchone()

    total_spend = float(spend_row[0]) if spend_row else 0.0
    avg_lv = round(float(spend_row[1]), 2) if spend_row else 0.0

    return {
        "total_customers": total,
        "one_time_customers": one_time,
        "returning_customers": returning,
        "returning_rate": round(returning / total * 100, 1) if total > 0 else 0.0,
        "total_spend": round(total_spend, 2),
        "avg_lifetime_value": avg_lv,
    }


def _change_pct(curr: float, prev: float) -> float:
    if prev == 0:
        return 0.0 if curr == 0 else 100.0
    return round(((curr - prev) / prev) * 100, 1)


def get_customer_summary(store_id: str, period: str = "30d") -> dict:
    """High-level customer metrics with period-over-period comparison."""
    conn = get_duckdb_connection()
    current_start, current_end, prev_start, prev_end = _parse_period_with_prev(period)

    current = _query_customer_metrics(conn, store_id, current_start, current_end)
    previous = _query_customer_metrics(conn, store_id, prev_start, prev_end)

    return {
        "current": current,
        "previous": previous,
        "changes": {
            "total_customers": _change_pct(current["total_customers"], previous["total_customers"]),
            "returning_rate": _change_pct(current["returning_rate"], previous["returning_rate"]),
            "total_spend": _change_pct(current["total_spend"], previous["total_spend"]),
            "avg_lifetime_value": _change_pct(current["avg_lifetime_value"], previous["avg_lifetime_value"]),
        },
    }


def get_top_customers(store_id: str, period: str = "30d", limit: int = 20) -> list[dict]:
    """Top customers by total spend in the period."""
    conn = get_duckdb_connection()
    start, end = _parse_period(period)

    rows = conn.execute(
        """
        SELECT
            customer_id,
            COUNT(DISTINCT order_id) AS order_count,
            SUM(total_price - discount_amount) AS total_spend,
            MIN(order_date) AS first_order,
            MAX(order_date) AS last_order,
            AVG(total_price - discount_amount) AS avg_order_value
        FROM orders
        WHERE store_id = ?
          AND order_date >= ?
          AND order_date <= ?
          AND status = 'completed'
        GROUP BY customer_id
        ORDER BY total_spend DESC
        LIMIT ?
        """,
        [store_id, start.isoformat(), end.isoformat(), limit],
    ).fetchall()

    return [
        {
            "customer_id": r[0],
            "order_count": int(r[1]),
            "total_spend": round(float(r[2]), 2),
            "first_order": r[3].isoformat() if r[3] else None,
            "last_order": r[4].isoformat() if r[4] else None,
            "avg_order_value": round(float(r[5]), 2),
        }
        for r in rows
    ]


def get_customer_segments(store_id: str, period: str = "30d") -> list[dict]:
    """RFM-based segmentation using Recency, Frequency, and Monetary scores."""
    conn = get_duckdb_connection()
    start, end = _parse_period(period)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    rows = conn.execute(
        """
        SELECT
            customer_id,
            SUM(total_price - discount_amount) AS total_spend,
            COUNT(DISTINCT order_id) AS order_count,
            MAX(order_date) AS last_order_date
        FROM orders
        WHERE store_id = ?
          AND order_date >= ?
          AND order_date <= ?
          AND status = 'completed'
        GROUP BY customer_id
        """,
        [store_id, start.isoformat(), end.isoformat()],
    ).fetchall()

    if not rows:
        return []

    spends = sorted(float(r[1]) for r in rows)
    freqs = sorted(int(r[2]) for r in rows)
    n = len(spends)

    spend_p25 = spends[int(n * 0.25)] if n > 1 else spends[0]
    spend_p75 = spends[int(n * 0.75)] if n > 1 else spends[0]
    freq_median = freqs[n // 2]

    segments: dict[str, list[dict]] = {
        "Champions": [],
        "Loyal": [],
        "Promising": [],
        "At Risk": [],
        "Needs Attention": [],
        "Lost": [],
    }

    for r in rows:
        spend = float(r[1])
        freq = int(r[2])
        last_dt = r[3]
        recency_days = (now - last_dt).days if last_dt else 999

        if period.endswith("m"):
            months = int(period[:-1])
            period_days = months * 30
        else:
            period_days = int(period.rstrip("d"))

        recent_threshold = period_days * 0.25
        medium_threshold = period_days * 0.6

        if recency_days <= recent_threshold and freq > freq_median and spend >= spend_p75:
            seg = "Champions"
        elif freq > freq_median and spend >= spend_p25:
            seg = "Loyal"
        elif recency_days <= recent_threshold and freq <= freq_median:
            seg = "Promising"
        elif recency_days <= medium_threshold and spend >= spend_p25:
            seg = "At Risk"
        elif recency_days <= medium_threshold:
            seg = "Needs Attention"
        else:
            seg = "Lost"

        segments[seg].append({"spend": spend})

    total_customers = sum(len(v) for v in segments.values())
    return [
        {
            "segment": name,
            "count": len(customers),
            "percentage": round(len(customers) / total_customers * 100, 1) if total_customers > 0 else 0,
            "total_spend": round(sum(c["spend"] for c in customers), 2),
            "avg_spend": round(sum(c["spend"] for c in customers) / len(customers), 2) if customers else 0,
        }
        for name, customers in segments.items()
        if len(customers) > 0
    ]


def get_customer_growth(store_id: str, period: str = "30d") -> list[dict]:
    """Customer growth time series — new and returning customers per day."""
    conn = get_duckdb_connection()
    start, end = _parse_period(period)

    rows = conn.execute(
        """
        WITH customer_first_order AS (
            SELECT customer_id, MIN(order_date) AS first_order_date
            FROM orders
            WHERE store_id = ?
              AND status = 'completed'
            GROUP BY customer_id
        ),
        daily_orders AS (
            SELECT
                CAST(o.order_date AS DATE) AS day,
                COUNT(DISTINCT o.customer_id) AS total,
                COUNT(DISTINCT CASE
                    WHEN CAST(cfo.first_order_date AS DATE) = CAST(o.order_date AS DATE)
                    THEN o.customer_id END) AS new_customers,
                COUNT(DISTINCT CASE
                    WHEN CAST(cfo.first_order_date AS DATE) < CAST(o.order_date AS DATE)
                    THEN o.customer_id END) AS returning_customers
            FROM orders o
            JOIN customer_first_order cfo ON o.customer_id = cfo.customer_id
            WHERE o.store_id = ?
              AND o.order_date >= ?
              AND o.order_date <= ?
              AND o.status = 'completed'
            GROUP BY CAST(o.order_date AS DATE)
            ORDER BY day
        )
        SELECT day, total, new_customers, returning_customers FROM daily_orders
        """,
        [store_id, store_id, start.isoformat(), end.isoformat()],
    ).fetchall()

    return [
        {
            "date": r[0].isoformat() if hasattr(r[0], 'isoformat') else str(r[0]),
            "total": int(r[1]),
            "new_customers": int(r[2]),
            "returning_customers": int(r[3]),
        }
        for r in rows
    ]
