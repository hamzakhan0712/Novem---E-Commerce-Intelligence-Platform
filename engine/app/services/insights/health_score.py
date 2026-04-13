"""
Business Health Score — composite 0-100 score that aggregates revenue growth,
customer health, operational efficiency, and trend momentum.
"""

import logging
from datetime import datetime, timedelta, timezone

from app.core.database import get_duckdb_connection
from app.services.dashboard.kpi_calculator import calculate_kpis

logger = logging.getLogger(__name__)

_PERIOD_DAYS = {
    "7d": 7, "14d": 14, "30d": 30, "60d": 60, "90d": 90,
    "6m": 182, "12m": 365,
}


def _period_start(period: str) -> str:
    days = _PERIOD_DAYS.get(period, 30)
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")


def calculate_health_score(store_id: str, period: str = "30d") -> dict:
    """Calculate a composite business health score (0-100)."""
    kpis = calculate_kpis(store_id, period)
    changes = kpis.get("changes", {})
    current = kpis.get("current", {})

    conn = get_duckdb_connection()
    start_date = _period_start(period)

    # Component 1: Revenue Growth Score (0-100)
    rev_change = changes.get("revenue", 0) or 0
    revenue_score = _map_score(rev_change, breakpoints=[-30, -10, 0, 10, 30], scores=[10, 30, 50, 70, 90])

    # Component 2: Customer Health Score (0-100)
    cust_change = changes.get("unique_customers", 0) or 0
    repeat_rate = _get_repeat_rate(conn, store_id, start_date)
    customer_score = (
        _map_score(cust_change, [-30, -10, 0, 10, 30], [10, 30, 50, 70, 90]) * 0.5 +
        _map_score(repeat_rate, [5, 15, 25, 35, 50], [15, 30, 50, 70, 90]) * 0.5
    )

    # Component 3: Operational Efficiency (0-100) — low refund rate + multi-channel
    refund_rate = _get_refund_rate(conn, store_id, start_date)
    channel_count = _get_channel_count(conn, store_id, start_date)
    efficiency_score = (
        _map_score(100 - refund_rate, [85, 90, 95, 98, 100], [20, 40, 60, 80, 95]) * 0.6 +
        _map_score(channel_count, [1, 2, 3, 4, 5], [20, 40, 60, 80, 95]) * 0.4
    )

    # Component 4: Growth Momentum (0-100) — consistency of revenue across sub-periods
    momentum_score = _get_momentum_score(conn, store_id, start_date, period)

    # Weighted composite
    weights = {
        "revenue_growth": 0.35,
        "customer_health": 0.25,
        "operational_efficiency": 0.20,
        "growth_momentum": 0.20,
    }

    overall = (
        revenue_score * weights["revenue_growth"]
        + customer_score * weights["customer_health"]
        + efficiency_score * weights["operational_efficiency"]
        + momentum_score * weights["growth_momentum"]
    )

    label = _score_label(overall)

    return {
        "overall_score": round(overall, 1),
        "label": label,
        "components": {
            "revenue_growth": {
                "score": round(revenue_score, 1),
                "weight": weights["revenue_growth"],
                "detail": f"Revenue change: {rev_change:+.1f}%",
            },
            "customer_health": {
                "score": round(customer_score, 1),
                "weight": weights["customer_health"],
                "detail": f"Customer change: {cust_change:+.1f}%, repeat rate: {repeat_rate:.0f}%",
            },
            "operational_efficiency": {
                "score": round(efficiency_score, 1),
                "weight": weights["operational_efficiency"],
                "detail": f"Refund rate: {refund_rate:.1f}%, channels: {channel_count}",
            },
            "growth_momentum": {
                "score": round(momentum_score, 1),
                "weight": weights["growth_momentum"],
                "detail": "Revenue trend consistency",
            },
        },
        "period": period,
    }


def _map_score(value: float, breakpoints: list[float], scores: list[float]) -> float:
    """Map a metric value to a score using linear interpolation between breakpoints."""
    if value <= breakpoints[0]:
        return scores[0]
    if value >= breakpoints[-1]:
        return scores[-1]
    for i in range(len(breakpoints) - 1):
        if breakpoints[i] <= value <= breakpoints[i + 1]:
            ratio = (value - breakpoints[i]) / (breakpoints[i + 1] - breakpoints[i])
            return scores[i] + ratio * (scores[i + 1] - scores[i])
    return scores[-1]


def _get_repeat_rate(conn, store_id: str, start_date: str) -> float:
    row = conn.execute(
        """SELECT
             COUNT(DISTINCT CASE WHEN oc > 1 THEN cid END) * 100.0 / NULLIF(COUNT(DISTINCT cid), 0)
           FROM (
             SELECT customer_id as cid, COUNT(DISTINCT order_id) as oc
             FROM orders WHERE store_id = ? AND order_date >= ? AND status = 'completed'
             GROUP BY customer_id
           )""",
        [store_id, start_date],
    ).fetchone()
    return float(row[0]) if row and row[0] is not None else 0


def _get_refund_rate(conn, store_id: str, start_date: str) -> float:
    row = conn.execute(
        """SELECT
             COUNT(DISTINCT CASE WHEN status = 'refunded' THEN order_id END) * 100.0
               / NULLIF(COUNT(DISTINCT CASE WHEN status IN ('completed', 'refunded') THEN order_id END), 0)
           FROM orders WHERE store_id = ? AND order_date >= ?""",
        [store_id, start_date],
    ).fetchone()
    return float(row[0]) if row and row[0] is not None else 0


def _get_channel_count(conn, store_id: str, start_date: str) -> int:
    row = conn.execute(
        "SELECT COUNT(DISTINCT channel) FROM orders WHERE store_id = ? AND order_date >= ? AND channel IS NOT NULL AND status = 'completed'",
        [store_id, start_date],
    ).fetchone()
    return int(row[0]) if row else 0


def _get_momentum_score(conn, store_id: str, start_date: str, period: str) -> float:
    """Score trend consistency by comparing weekly revenue sub-periods."""
    rows = conn.execute(
        """SELECT
             DATE_TRUNC('week', order_date::DATE) as week,
             SUM(total_price - discount_amount) as rev
           FROM orders WHERE store_id = ? AND order_date >= ? AND status = 'completed'
           GROUP BY week ORDER BY week""",
        [store_id, start_date],
    ).fetchall()

    if len(rows) < 3:
        return 50.0

    revenues = [float(r[1]) for r in rows]
    # Count how many weeks showed growth
    growths = sum(1 for i in range(1, len(revenues)) if revenues[i] >= revenues[i - 1])
    growth_ratio = growths / (len(revenues) - 1)
    return _map_score(growth_ratio * 100, [20, 35, 50, 65, 80], [15, 35, 50, 70, 90])


def _score_label(score: float) -> str:
    if score >= 80:
        return "Excellent"
    if score >= 65:
        return "Good"
    if score >= 45:
        return "Fair"
    if score >= 25:
        return "Needs Attention"
    return "Critical"
