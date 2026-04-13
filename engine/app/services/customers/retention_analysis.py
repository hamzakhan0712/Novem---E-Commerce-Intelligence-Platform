"""
Retention cohort analysis — focused retention metrics beyond
the cohort replay system. Provides retention curves, churn
rate by cohort, period-over-period retention trends, and
first-purchase-to-repeat conversion timing.
"""

import logging

from app.core.database import get_duckdb_connection

logger = logging.getLogger(__name__)


def get_retention_curves(store_id: str, max_months: int = 12) -> dict:
    """Compute averaged retention curves across all cohorts."""
    conn = get_duckdb_connection()

    rows = conn.execute(
        """
        WITH customer_cohort AS (
            SELECT customer_id,
                   DATE_TRUNC('month', MIN(order_date)) AS cohort_date
            FROM orders
            WHERE store_id = ? AND status = 'completed'
            GROUP BY customer_id
        ),
        activity AS (
            SELECT o.customer_id,
                   c.cohort_date,
                   DATE_DIFF('month', c.cohort_date, DATE_TRUNC('month', o.order_date)) AS month_offset
            FROM orders o
            JOIN customer_cohort c ON o.customer_id = c.customer_id
            WHERE o.store_id = ? AND o.status = 'completed'
        ),
        cohort_sizes AS (
            SELECT cohort_date, COUNT(DISTINCT customer_id) AS size
            FROM customer_cohort
            GROUP BY cohort_date
        )
        SELECT a.month_offset,
               SUM(cs.size) AS total_cohort_size,
               COUNT(DISTINCT a.customer_id) AS retained
        FROM activity a
        JOIN cohort_sizes cs ON a.cohort_date = cs.cohort_date
        WHERE a.month_offset >= 0 AND a.month_offset < ?
        GROUP BY a.month_offset
        ORDER BY a.month_offset
        """,
        [store_id, store_id, max_months],
    ).fetchall()

    if not rows:
        return {"curve": [], "summary": {}}

    curve = []
    for row in rows:
        offset = int(row[0])
        total_size = int(row[1])
        retained = int(row[2])
        pct = round(retained / total_size * 100, 1) if total_size > 0 else 0
        curve.append({
            "month": offset,
            "retention_pct": pct,
            "retained_count": retained,
            "total_cohort_size": total_size,
        })

    return {
        "curve": curve,
        "summary": {
            "month_0": curve[0]["retention_pct"] if curve else 0,
            "month_1": next((c["retention_pct"] for c in curve if c["month"] == 1), 0),
            "month_3": next((c["retention_pct"] for c in curve if c["month"] == 3), 0),
            "month_6": next((c["retention_pct"] for c in curve if c["month"] == 6), 0),
        },
    }


def get_repeat_purchase_timing(store_id: str) -> dict:
    """Distribution of days between first and second purchase."""
    conn = get_duckdb_connection()

    rows = conn.execute(
        """
        WITH ranked AS (
            SELECT customer_id, order_date,
                   ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date) AS rn
            FROM orders
            WHERE store_id = ? AND status = 'completed'
        )
        SELECT DATE_DIFF('day', r1.order_date, r2.order_date) AS days_to_repeat
        FROM ranked r1
        JOIN ranked r2 ON r1.customer_id = r2.customer_id AND r1.rn = 1 AND r2.rn = 2
        """,
        [store_id],
    ).fetchall()

    if not rows:
        return {"distribution": [], "summary": {}}

    days = [int(r[0]) for r in rows if r[0] is not None and int(r[0]) > 0]
    if not days:
        return {"distribution": [], "summary": {}}

    buckets = {"1-7 days": 0, "8-14 days": 0, "15-30 days": 0, "31-60 days": 0, "61-90 days": 0, "90+ days": 0}
    for d in days:
        if d <= 7:
            buckets["1-7 days"] += 1
        elif d <= 14:
            buckets["8-14 days"] += 1
        elif d <= 30:
            buckets["15-30 days"] += 1
        elif d <= 60:
            buckets["31-60 days"] += 1
        elif d <= 90:
            buckets["61-90 days"] += 1
        else:
            buckets["90+ days"] += 1

    distribution = [{"bucket": k, "count": v} for k, v in buckets.items()]
    avg_days = round(sum(days) / len(days), 1)
    median_days = sorted(days)[len(days) // 2]

    return {
        "distribution": distribution,
        "summary": {
            "avg_days_to_repeat": avg_days,
            "median_days_to_repeat": median_days,
            "total_repeat_customers": len(days),
        },
    }


def get_churn_by_cohort(store_id: str, max_months: int = 12) -> dict:
    """Monthly churn rate (1 - retention) per cohort."""
    conn = get_duckdb_connection()

    rows = conn.execute(
        """
        WITH customer_cohort AS (
            SELECT customer_id,
                   STRFTIME(DATE_TRUNC('month', MIN(order_date)), '%Y-%m') AS cohort_month
            FROM orders
            WHERE store_id = ? AND status = 'completed'
            GROUP BY customer_id
        ),
        cohort_sizes AS (
            SELECT cohort_month, COUNT(*) AS size
            FROM customer_cohort
            GROUP BY cohort_month
        ),
        activity AS (
            SELECT c.cohort_month,
                   STRFTIME(DATE_TRUNC('month', o.order_date), '%Y-%m') AS activity_month,
                   COUNT(DISTINCT o.customer_id) AS active_count
            FROM orders o
            JOIN customer_cohort c ON o.customer_id = c.customer_id
            WHERE o.store_id = ? AND o.status = 'completed'
            GROUP BY c.cohort_month, STRFTIME(DATE_TRUNC('month', o.order_date), '%Y-%m')
        )
        SELECT a.cohort_month, cs.size, a.activity_month, a.active_count
        FROM activity a
        JOIN cohort_sizes cs ON a.cohort_month = cs.cohort_month
        ORDER BY a.cohort_month, a.activity_month
        """,
        [store_id, store_id],
    ).fetchall()

    if not rows:
        return {"cohorts": []}

    cohort_map: dict[str, dict] = {}
    for row in rows:
        cm = row[0]
        size = int(row[1])
        active = int(row[3])
        if cm not in cohort_map:
            cohort_map[cm] = {"cohort_month": cm, "size": size, "active_history": []}
        retention = round(active / size * 100, 1) if size > 0 else 0
        churn = round(100 - retention, 1)
        cohort_map[cm]["active_history"].append({
            "month": row[2],
            "active": active,
            "retention_pct": retention,
            "churn_pct": churn,
        })

    cohorts = list(cohort_map.values())[-max_months:]
    return {"cohorts": cohorts}
