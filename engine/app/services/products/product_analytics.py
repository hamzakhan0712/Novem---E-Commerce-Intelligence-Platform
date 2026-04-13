"""
Product analytics — Computes product metrics from DuckDB orders table.
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


def _change_pct(curr: float, prev: float) -> float:
    if prev == 0:
        return 0.0 if curr == 0 else 100.0
    return round(((curr - prev) / prev) * 100, 1)


def _query_product_metrics(conn, store_id: str, start: datetime, end: datetime) -> dict:
    """Compute product metrics for a single period."""
    row = conn.execute(
        """
        SELECT
            COUNT(DISTINCT product_id) AS products_sold,
            COUNT(DISTINCT category) AS categories,
            COALESCE(SUM(quantity), 0) AS total_units,
            COALESCE(SUM(total_price - discount_amount), 0) AS total_revenue,
            COALESCE(AVG(unit_price), 0) AS avg_price
        FROM orders
        WHERE store_id = ?
          AND order_date >= ?
          AND order_date <= ?
          AND status = 'completed'
        """,
        [store_id, start.isoformat(), end.isoformat()],
    ).fetchone()

    if not row or int(row[0]) == 0:
        return {
            "products_sold": 0,
            "categories": 0,
            "total_units": 0,
            "total_revenue": 0.0,
            "avg_price": 0.0,
        }

    return {
        "products_sold": int(row[0]),
        "categories": int(row[1]),
        "total_units": int(row[2]),
        "total_revenue": round(float(row[3]), 2),
        "avg_price": round(float(row[4]), 2),
    }


def get_product_summary(store_id: str, period: str = "30d") -> dict:
    """High-level product metrics with period-over-period comparison."""
    conn = get_duckdb_connection()
    current_start, current_end, prev_start, prev_end = _parse_period_with_prev(period)

    current = _query_product_metrics(conn, store_id, current_start, current_end)
    previous = _query_product_metrics(conn, store_id, prev_start, prev_end)

    return {
        "current": current,
        "previous": previous,
        "changes": {
            "products_sold": _change_pct(current["products_sold"], previous["products_sold"]),
            "total_units": _change_pct(current["total_units"], previous["total_units"]),
            "total_revenue": _change_pct(current["total_revenue"], previous["total_revenue"]),
            "avg_price": _change_pct(current["avg_price"], previous["avg_price"]),
        },
    }


def get_top_products(store_id: str, period: str = "30d", sort_by: str = "revenue", limit: int = 20) -> list[dict]:
    """Top products sorted by revenue or units sold."""
    conn = get_duckdb_connection()
    start, end = _parse_period(period)

    order_col = "total_revenue DESC" if sort_by == "revenue" else "total_units DESC"

    rows = conn.execute(
        f"""
        SELECT
            product_id,
            COALESCE(MAX(product_name), product_id) AS product_name,
            MAX(category) AS category,
            SUM(quantity) AS total_units,
            SUM(total_price - discount_amount) AS total_revenue,
            AVG(unit_price) AS avg_price,
            COUNT(DISTINCT order_id) AS order_count,
            COUNT(DISTINCT customer_id) AS unique_buyers
        FROM orders
        WHERE store_id = ?
          AND order_date >= ?
          AND order_date <= ?
          AND status = 'completed'
        GROUP BY product_id
        ORDER BY {order_col}
        LIMIT ?
        """,
        [store_id, start.isoformat(), end.isoformat(), limit],
    ).fetchall()

    return [
        {
            "product_id": r[0],
            "product_name": r[1],
            "category": r[2],
            "total_units": int(r[3]),
            "total_revenue": round(float(r[4]), 2),
            "avg_price": round(float(r[5]), 2),
            "order_count": int(r[6]),
            "unique_buyers": int(r[7]),
        }
        for r in rows
    ]


def get_category_breakdown(store_id: str, period: str = "30d") -> list[dict]:
    """Revenue and units breakdown by category with avg price."""
    conn = get_duckdb_connection()
    start, end = _parse_period(period)

    rows = conn.execute(
        """
        SELECT
            COALESCE(category, 'Uncategorized') AS category,
            COUNT(DISTINCT product_id) AS product_count,
            SUM(quantity) AS total_units,
            SUM(total_price - discount_amount) AS total_revenue,
            AVG(unit_price) AS avg_price,
            COUNT(DISTINCT customer_id) AS unique_buyers
        FROM orders
        WHERE store_id = ?
          AND order_date >= ?
          AND order_date <= ?
          AND status = 'completed'
        GROUP BY category
        ORDER BY total_revenue DESC
        """,
        [store_id, start.isoformat(), end.isoformat()],
    ).fetchall()

    total_rev = sum(float(r[3]) for r in rows) if rows else 0

    return [
        {
            "category": r[0],
            "product_count": int(r[1]),
            "total_units": int(r[2]),
            "total_revenue": round(float(r[3]), 2),
            "percentage": round(float(r[3]) / total_rev * 100, 1) if total_rev > 0 else 0,
            "avg_price": round(float(r[4]), 2),
            "unique_buyers": int(r[5]),
        }
        for r in rows
    ]


def get_product_revenue_trend(store_id: str, period: str = "30d") -> list[dict]:
    """Daily product revenue and units time-series."""
    conn = get_duckdb_connection()
    start, end = _parse_period(period)

    rows = conn.execute(
        """
        SELECT
            CAST(order_date AS DATE) AS day,
            SUM(total_price - discount_amount) AS revenue,
            SUM(quantity) AS units,
            COUNT(DISTINCT order_id) AS orders
        FROM orders
        WHERE store_id = ?
          AND order_date >= ?
          AND order_date <= ?
          AND status = 'completed'
        GROUP BY CAST(order_date AS DATE)
        ORDER BY day
        """,
        [store_id, start.isoformat(), end.isoformat()],
    ).fetchall()

    return [
        {
            "date": r[0].isoformat() if hasattr(r[0], 'isoformat') else str(r[0]),
            "revenue": round(float(r[1]), 2),
            "units": int(r[2]),
            "orders": int(r[3]),
        }
        for r in rows
    ]
