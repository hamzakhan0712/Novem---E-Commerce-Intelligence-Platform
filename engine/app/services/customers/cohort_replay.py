"""
Cohort Replay — Time-travel customer cohort analysis.

Lets you pick any past month and replay exactly what your customer
cohort looked like at that point in time — retention curves, AOV,
revenue — as if you were back in that month looking forward.
"""

import logging
from datetime import datetime, timedelta

from app.core.database import get_duckdb_connection

logger = logging.getLogger(__name__)


def get_cohort_replay(
    store_id: str,
    replay_month: str | None = None,
    max_months: int = 12,
) -> dict:
    """Build cohort retention data, optionally filtered to a replay point in time."""
    conn = get_duckdb_connection()

    try:
        available = conn.execute(
            """
            SELECT DISTINCT STRFTIME(DATE_TRUNC('month', order_date), '%Y-%m') AS m
            FROM orders
            WHERE store_id = ? AND status = 'completed'
            ORDER BY m
            """,
            [store_id],
        ).fetchall()
        available_months = [r[0] for r in available]

        if not available_months:
            return {
                "replay_month": None,
                "available_months": [],
                "cohorts": [],
                "overall_retention": [],
                "summary": {"total_cohorts": 0, "total_customers": 0},
            }

        if replay_month and replay_month in available_months:
            effective_replay = replay_month
        else:
            effective_replay = available_months[-1]

        rows = conn.execute(
            """
            WITH customer_cohort AS (
                SELECT
                    customer_id,
                    STRFTIME(MIN(DATE_TRUNC('month', order_date)), '%Y-%m') AS cohort_month
                FROM orders
                WHERE store_id = ? AND status = 'completed'
                  AND STRFTIME(DATE_TRUNC('month', order_date), '%Y-%m') <= ?
                GROUP BY customer_id
            ),
            monthly_activity AS (
                SELECT
                    o.customer_id,
                    c.cohort_month,
                    STRFTIME(DATE_TRUNC('month', o.order_date), '%Y-%m') AS activity_month,
                    SUM(o.total_price - o.discount_amount) AS revenue,
                    COUNT(*) AS order_count
                FROM orders o
                JOIN customer_cohort c ON o.customer_id = c.customer_id
                WHERE o.store_id = ? AND o.status = 'completed'
                  AND STRFTIME(DATE_TRUNC('month', o.order_date), '%Y-%m') <= ?
                GROUP BY o.customer_id, c.cohort_month, STRFTIME(DATE_TRUNC('month', o.order_date), '%Y-%m')
            ),
            cohort_sizes AS (
                SELECT cohort_month, COUNT(*) AS cohort_size
                FROM customer_cohort
                GROUP BY cohort_month
            )
            SELECT
                ma.cohort_month,
                cs.cohort_size,
                ma.activity_month,
                COUNT(DISTINCT ma.customer_id) AS retained_count,
                COALESCE(AVG(ma.revenue), 0) AS avg_revenue,
                COALESCE(SUM(ma.revenue), 0) AS total_revenue
            FROM monthly_activity ma
            JOIN cohort_sizes cs ON ma.cohort_month = cs.cohort_month
            GROUP BY ma.cohort_month, cs.cohort_size, ma.activity_month
            ORDER BY ma.cohort_month, ma.activity_month
            """,
            [store_id, effective_replay, store_id, effective_replay],
        ).fetchall()

        cohort_map: dict[str, dict] = {}
        all_month_indices: set[int] = set()

        for row in rows:
            cohort_m = row[0]
            cohort_size = int(row[1])
            activity_m = row[2]
            retained = int(row[3])
            aov = round(float(row[4]), 2)
            revenue = round(float(row[5]), 2)

            month_idx = _month_diff(cohort_m, activity_m)
            if month_idx < 0 or month_idx >= max_months:
                continue

            if cohort_m not in cohort_map:
                cohort_map[cohort_m] = {"cohort_month": cohort_m, "size": cohort_size, "months": {}}

            retention_pct = round(retained / cohort_size * 100, 1) if cohort_size > 0 else 0
            cohort_map[cohort_m]["months"][month_idx] = {
                "month_index": month_idx,
                "retained_count": retained,
                "retention_pct": retention_pct,
                "aov": aov,
                "revenue": revenue,
            }
            all_month_indices.add(month_idx)

        cohorts = []
        for cm in sorted(cohort_map.keys()):
            entry = cohort_map[cm]
            months_list = []
            for idx in sorted(entry["months"].keys()):
                months_list.append(entry["months"][idx])
            cohorts.append({
                "cohort_month": entry["cohort_month"],
                "size": entry["size"],
                "months": months_list,
            })

        max_idx = max(all_month_indices) if all_month_indices else 0
        overall_retention = []
        for idx in range(max_idx + 1):
            total_retained = 0
            total_size = 0
            for c in cohorts:
                month_data = next((m for m in c["months"] if m["month_index"] == idx), None)
                if month_data:
                    total_retained += month_data["retained_count"]
                    total_size += c["size"]
            pct = round(total_retained / total_size * 100, 1) if total_size > 0 else 0
            overall_retention.append(pct)

        total_customers = sum(c["size"] for c in cohorts)

        months_visible = [m for m in available_months if m <= effective_replay]

        return {
            "replay_month": effective_replay,
            "available_months": months_visible,
            "cohorts": cohorts[-max_months:],
            "overall_retention": overall_retention,
            "summary": {
                "total_cohorts": len(cohorts),
                "total_customers": total_customers,
                "avg_month0_retention": overall_retention[0] if overall_retention else 0,
                "avg_month1_retention": overall_retention[1] if len(overall_retention) > 1 else 0,
            },
        }

    except Exception as exc:
        logger.error("Cohort replay failed: %s", exc)
        return {
            "replay_month": replay_month,
            "available_months": [],
            "cohorts": [],
            "overall_retention": [],
            "summary": {"total_cohorts": 0, "total_customers": 0},
            "message": str(exc),
        }


def _month_diff(start_month: str, end_month: str) -> int:
    """Calculate the number of months between two YYYY-MM strings."""
    try:
        s = datetime.strptime(start_month, "%Y-%m")
        e = datetime.strptime(end_month, "%Y-%m")
        return (e.year - s.year) * 12 + (e.month - s.month)
    except (ValueError, TypeError):
        return -1
