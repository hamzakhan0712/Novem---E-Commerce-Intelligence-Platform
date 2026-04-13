"""
Dead Weight Detector — Product lifecycle classifier.

Classifies every product into one of 4 lifecycle stages based on
revenue trend + order velocity + review sentiment:
- Rising Star: growing fast
- Cash Cow: stable high performer
- Fading Out: declining but not hated
- Dead Weight: declining + disliked or abandoned
"""

import logging
from datetime import datetime, timedelta, timezone

from app.core.database import get_duckdb_connection

logger = logging.getLogger(__name__)

_PERIOD_DAYS = {
    "7d": 7, "14d": 14, "30d": 30, "60d": 60, "90d": 90,
    "6m": 182, "12m": 365,
}

_RECOMMENDATIONS = {
    "rising_star": "Increase marketing spend and ensure inventory is stocked — this product is gaining momentum.",
    "cash_cow": "Maintain current strategy. This product delivers consistent returns.",
    "fading_out": "Consider a promotional campaign or product refresh to reverse the decline.",
    "dead_weight": "Evaluate discontinuing this product or running a deep clearance sale.",
}


def classify_product_lifecycle(store_id: str, period: str = "6m") -> dict:
    """Classify each product into a lifecycle stage."""
    conn = get_duckdb_connection()
    days = _PERIOD_DAYS.get(period, 182)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    midpoint = (now - timedelta(days=days // 2)).strftime("%Y-%m-%d")
    today = now.strftime("%Y-%m-%d")

    try:
        product_rows = conn.execute(
            """
            WITH early AS (
                SELECT
                    product_id,
                    COALESCE(product_name, product_id) AS product_name,
                    COALESCE(category, 'Uncategorized') AS category,
                    SUM(total_price - discount_amount) AS revenue,
                    COUNT(*) AS order_count
                FROM orders
                WHERE store_id = ? AND order_date >= ? AND order_date < ? AND status = 'completed'
                GROUP BY product_id, product_name, category
            ),
            recent AS (
                SELECT
                    product_id,
                    SUM(total_price - discount_amount) AS revenue,
                    COUNT(*) AS order_count
                FROM orders
                WHERE store_id = ? AND order_date >= ? AND order_date <= ? AND status = 'completed'
                GROUP BY product_id
            ),
            combined AS (
                SELECT
                    COALESCE(e.product_id, r.product_id) AS product_id,
                    COALESCE(e.product_name, COALESCE(r.product_id, 'Unknown')) AS product_name,
                    COALESCE(e.category, 'Uncategorized') AS category,
                    COALESCE(e.revenue, 0) AS early_revenue,
                    COALESCE(e.order_count, 0) AS early_orders,
                    COALESCE(r.revenue, 0) AS recent_revenue,
                    COALESCE(r.order_count, 0) AS recent_orders,
                    COALESCE(e.revenue, 0) + COALESCE(r.revenue, 0) AS total_revenue,
                    COALESCE(e.order_count, 0) + COALESCE(r.order_count, 0) AS total_orders
                FROM early e
                FULL OUTER JOIN recent r ON e.product_id = r.product_id
            )
            SELECT * FROM combined ORDER BY total_revenue DESC
            """,
            [store_id, cutoff, midpoint, store_id, midpoint, today],
        ).fetchall()

        columns = [
            "product_id", "product_name", "category",
            "early_revenue", "early_orders", "recent_revenue", "recent_orders",
            "total_revenue", "total_orders",
        ]

        sentiment_map = _get_product_sentiments(conn, store_id, cutoff, today)

        median_revenue = _median([float(r[7]) for r in product_rows]) if product_rows else 0

        products = []
        summary = {"rising_star": 0, "cash_cow": 0, "fading_out": 0, "dead_weight": 0}

        for row in product_rows:
            rec = dict(zip(columns, row))
            early_rev = float(rec["early_revenue"])
            recent_rev = float(rec["recent_revenue"])
            early_ord = int(rec["early_orders"])
            recent_ord = int(rec["recent_orders"])
            total_rev = float(rec["total_revenue"])

            if early_rev > 0:
                revenue_trend = (recent_rev - early_rev) / early_rev
            elif recent_rev > 0:
                revenue_trend = 1.0
            else:
                revenue_trend = 0.0

            if early_ord > 0:
                velocity_score = (recent_ord - early_ord) / early_ord
            elif recent_ord > 0:
                velocity_score = 1.0
            else:
                velocity_score = -1.0

            sentiment = sentiment_map.get(rec["product_id"], 0.5)

            stage = _classify(revenue_trend, velocity_score, sentiment, total_rev, median_revenue, recent_ord)
            summary[stage] += 1

            products.append({
                "product_id": rec["product_id"],
                "product_name": rec["product_name"],
                "category": rec["category"],
                "lifecycle_stage": stage,
                "revenue_trend": round(revenue_trend, 3),
                "velocity_score": round(velocity_score, 3),
                "sentiment_score": round(sentiment, 3),
                "total_revenue": round(total_rev, 2),
                "recent_revenue": round(recent_rev, 2),
                "order_count": int(rec["total_orders"]),
                "recommendation": _RECOMMENDATIONS[stage],
            })

        return {
            "products": products,
            "summary": summary,
            "period": period,
            "total_products": len(products),
        }

    except Exception as exc:
        logger.error("Product lifecycle classification failed: %s", exc)
        return {
            "products": [],
            "summary": {"rising_star": 0, "cash_cow": 0, "fading_out": 0, "dead_weight": 0},
            "period": period,
            "total_products": 0,
            "message": str(exc),
        }


def _classify(
    trend: float, velocity: float, sentiment: float,
    total_rev: float, median_rev: float, recent_orders: int,
) -> str:
    """BCG-inspired classification based on 3 signals."""
    if recent_orders == 0:
        return "dead_weight"

    if trend > 0.1 and velocity > 0:
        return "rising_star"

    if -0.1 <= trend <= 0.1 and total_rev >= median_rev:
        return "cash_cow"

    if trend < -0.1:
        if sentiment < 0.4:
            return "dead_weight"
        return "fading_out"

    if total_rev >= median_rev:
        return "cash_cow"

    return "fading_out"


def _get_product_sentiments(conn, store_id: str, cutoff: str, today: str) -> dict[str, float]:
    """Get avg sentiment per product from reviews table."""
    try:
        rows = conn.execute(
            """
            SELECT product_id, AVG(sentiment_score) AS avg_sent
            FROM reviews
            WHERE store_id = ?
              AND review_date >= ?
              AND review_date <= ?
              AND sentiment_score IS NOT NULL
            GROUP BY product_id
            """,
            [store_id, cutoff, today],
        ).fetchall()
        return {r[0]: float(r[1]) for r in rows}
    except Exception:
        return {}


def _median(values: list[float]) -> float:
    """Simple median calculation."""
    if not values:
        return 0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 0:
        return (s[mid - 1] + s[mid]) / 2
    return s[mid]
