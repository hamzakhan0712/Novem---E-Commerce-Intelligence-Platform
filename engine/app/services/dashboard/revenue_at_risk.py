"""
Revenue At Risk — calculates future revenue at risk of being lost
based on customer purchase gap patterns.

For each customer, compares days since last purchase against their
personal average purchase gap. Customers exceeding 1.5× their gap
are flagged as "at risk". Their expected spend is the dollar value
that may be lost in the next lookahead window.
"""

import logging
from datetime import datetime, timedelta, timezone

from app.core.database import get_duckdb_connection

logger = logging.getLogger(__name__)

_PERIOD_DAYS = {
    "7d": 7, "14d": 14, "30d": 30, "60d": 60, "90d": 90,
    "6m": 182, "12m": 365,
}


def calculate_revenue_at_risk(
    store_id: str,
    period: str = "12m",
    lookahead_days: int = 30,
) -> dict:
    """Identify customers whose purchase patterns suggest imminent churn
    and quantify the revenue at stake."""
    conn = get_duckdb_connection()
    days = _PERIOD_DAYS.get(period, 365)
    cutoff = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)).strftime("%Y-%m-%d")
    today = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d")

    try:
        rows = conn.execute(
            """
            WITH customer_orders AS (
                SELECT
                    customer_id,
                    CAST(order_date AS DATE) AS order_day,
                    SUM(total_price - discount_amount) AS day_spend
                FROM orders
                WHERE store_id = ?
                  AND order_date >= ?
                  AND status = 'completed'
                GROUP BY customer_id, CAST(order_date AS DATE)
            ),
            customer_metrics AS (
                SELECT
                    customer_id,
                    COUNT(*) AS visit_count,
                    MIN(order_day) AS first_order,
                    MAX(order_day) AS last_order,
                    SUM(day_spend) AS total_spend,
                    SUM(day_spend) / COUNT(*) AS avg_visit_spend,
                    CASE
                        WHEN COUNT(*) > 1
                        THEN CAST(last_order - first_order AS INTEGER) / (COUNT(*) - 1.0)
                        ELSE NULL
                    END AS avg_gap_days,
                    CAST(? AS DATE) - MAX(order_day) AS days_since_last
                FROM customer_orders
                GROUP BY customer_id
                HAVING COUNT(*) >= 2
            )
            SELECT
                customer_id,
                visit_count,
                avg_gap_days,
                days_since_last,
                avg_visit_spend,
                total_spend,
                days_since_last - avg_gap_days AS days_overdue
            FROM customer_metrics
            WHERE avg_gap_days IS NOT NULL
              AND avg_gap_days > 0
              AND days_since_last > avg_gap_days * 1.5
            ORDER BY avg_visit_spend DESC
            """,
            [store_id, cutoff, today],
        ).fetchall()

        columns = [
            "customer_id", "visit_count", "avg_gap_days",
            "days_since_last", "avg_visit_spend", "total_spend", "days_overdue",
        ]

        total_analyzed_row = conn.execute(
            """
            SELECT COUNT(DISTINCT customer_id)
            FROM orders
            WHERE store_id = ? AND order_date >= ? AND status = 'completed'
            """,
            [store_id, cutoff],
        ).fetchone()
        total_analyzed = total_analyzed_row[0] if total_analyzed_row else 0

        customers = []
        total_at_risk = 0.0
        sum_overdue = 0.0

        for row in rows:
            rec = dict(zip(columns, row))
            avg_gap = float(rec["avg_gap_days"]) if rec["avg_gap_days"] else 1
            aov = float(rec["avg_visit_spend"])
            overdue = float(rec["days_overdue"])
            days_since = float(rec["days_since_last"])

            expected_purchases = max(1, lookahead_days / avg_gap)
            estimated_loss = round(aov * expected_purchases, 2)
            total_at_risk += estimated_loss
            sum_overdue += overdue

            customers.append({
                "customer_id": rec["customer_id"],
                "visit_count": int(rec["visit_count"]),
                "avg_gap_days": round(avg_gap, 1),
                "days_since_last": int(days_since),
                "days_overdue": round(overdue, 1),
                "historical_aov": round(aov, 2),
                "total_spend": round(float(rec["total_spend"]), 2),
                "estimated_loss": estimated_loss,
            })

        avg_overdue = round(sum_overdue / len(customers), 1) if customers else 0

        return {
            "total_at_risk": round(total_at_risk, 2),
            "customers_at_risk": len(customers),
            "total_customers_analyzed": total_analyzed,
            "avg_days_overdue": avg_overdue,
            "lookahead_days": lookahead_days,
            "period": period,
            "top_at_risk_customers": customers[:20],
        }

    except Exception as exc:
        logger.error("Revenue at risk calculation failed: %s", exc)
        return {
            "total_at_risk": 0,
            "customers_at_risk": 0,
            "total_customers_analyzed": 0,
            "avg_days_overdue": 0,
            "lookahead_days": lookahead_days,
            "period": period,
            "top_at_risk_customers": [],
            "message": str(exc),
        }
