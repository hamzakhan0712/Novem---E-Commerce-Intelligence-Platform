"""
Business DNA — Store fingerprinting algorithm.

Analyzes store data patterns and generates a unique Business DNA profile
with 6 dimensions scored 0-100: Growth Velocity, Customer Loyalty,
Product Diversity, Revenue Stability, Discount Dependency, Seasonal Sensitivity.

Classifies the store into an archetype based on its strongest dimensions.
"""

import logging
import math
from datetime import datetime, timedelta, timezone

from app.core.database import get_duckdb_connection
from app.services.currency.currency_helper import sym as _sym

logger = logging.getLogger(__name__)

_PERIOD_DAYS = {
    "7d": 7, "14d": 14, "30d": 30, "60d": 60, "90d": 90,
    "6m": 182, "12m": 365,
}

_ARCHETYPES = {
    ("Growth Velocity", "Customer Loyalty"): {
        "name": "Growth Machine",
        "description": "Your store is expanding rapidly while retaining a loyal customer base — a rare and powerful combination.",
    },
    ("Customer Loyalty", "Growth Velocity"): {
        "name": "Growth Machine",
        "description": "Your store is expanding rapidly while retaining a loyal customer base — a rare and powerful combination.",
    },
    ("Customer Loyalty", "Revenue Stability"): {
        "name": "Loyalty Fortress",
        "description": "Your business is built on repeat customers and predictable revenue — the hallmark of a sustainable operation.",
    },
    ("Revenue Stability", "Customer Loyalty"): {
        "name": "Loyalty Fortress",
        "description": "Your business is built on repeat customers and predictable revenue — the hallmark of a sustainable operation.",
    },
    ("Product Diversity", "Revenue Stability"): {
        "name": "Diversified Stable",
        "description": "Revenue is spread evenly across categories with low volatility — you're resilient to market shifts.",
    },
    ("Revenue Stability", "Product Diversity"): {
        "name": "Diversified Stable",
        "description": "Revenue is spread evenly across categories with low volatility — you're resilient to market shifts.",
    },
    ("Growth Velocity", "Product Diversity"): {
        "name": "Rising Empire",
        "description": "Fast growth across a diverse product catalog — you're scaling in multiple directions at once.",
    },
    ("Product Diversity", "Growth Velocity"): {
        "name": "Rising Empire",
        "description": "Fast growth across a diverse product catalog — you're scaling in multiple directions at once.",
    },
}

_DEFAULT_ARCHETYPE = {
    "name": "Balanced Operator",
    "description": "Your business shows balanced performance across dimensions — solid foundations with room for specialization.",
}


def calculate_business_dna(store_id: str, period: str = "12m") -> dict:
    """Calculate the 6-dimension Business DNA fingerprint for a store."""
    conn = get_duckdb_connection()
    days = _PERIOD_DAYS.get(period, 365)
    cutoff = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)).strftime("%Y-%m-%d")
    today = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d")

    try:
        growth = _growth_velocity(conn, store_id, cutoff, today)
        loyalty = _customer_loyalty(conn, store_id, cutoff, today)
        diversity = _product_diversity(conn, store_id, cutoff, today)
        stability = _revenue_stability(conn, store_id, cutoff, today)
        discount_dep = _discount_dependency(conn, store_id, cutoff, today)
        seasonal = _seasonal_sensitivity(conn, store_id, cutoff, today)

        dimensions = [
            {"name": "Growth Velocity", "score": growth["score"], "label": growth["label"], "detail": growth["detail"]},
            {"name": "Customer Loyalty", "score": loyalty["score"], "label": loyalty["label"], "detail": loyalty["detail"]},
            {"name": "Product Diversity", "score": diversity["score"], "label": diversity["label"], "detail": diversity["detail"]},
            {"name": "Revenue Stability", "score": stability["score"], "label": stability["label"], "detail": stability["detail"]},
            {"name": "Discount Dependency", "score": discount_dep["score"], "label": discount_dep["label"], "detail": discount_dep["detail"]},
            {"name": "Seasonal Sensitivity", "score": seasonal["score"], "label": seasonal["label"], "detail": seasonal["detail"]},
        ]

        sorted_dims = sorted(dimensions, key=lambda d: d["score"], reverse=True)
        top_two = (sorted_dims[0]["name"], sorted_dims[1]["name"])
        archetype_info = _ARCHETYPES.get(top_two, _DEFAULT_ARCHETYPE)

        avg_score = sum(d["score"] for d in dimensions) / len(dimensions)
        summary = f"Overall DNA strength: {avg_score:.0f}/100. Strongest: {sorted_dims[0]['name']} ({sorted_dims[0]['score']}). Weakest: {sorted_dims[-1]['name']} ({sorted_dims[-1]['score']})."

        return {
            "dimensions": dimensions,
            "archetype": archetype_info["name"],
            "archetype_description": archetype_info["description"],
            "summary": summary,
            "period": period,
        }

    except Exception as exc:
        logger.error("Business DNA calculation failed: %s", exc)
        return {
            "dimensions": [],
            "archetype": "Unknown",
            "archetype_description": "Insufficient data to determine business archetype.",
            "summary": "Unable to calculate Business DNA.",
            "period": period,
            "message": str(exc),
        }


def _growth_velocity(conn, store_id: str, cutoff: str, today: str) -> dict:
    """Linear regression slope on monthly revenue, normalized to 0-100."""
    rows = conn.execute(
        """
        SELECT
            DATE_TRUNC('month', order_date) AS month,
            SUM(total_price - discount_amount) AS revenue
        FROM orders
        WHERE store_id = ? AND order_date >= ? AND order_date <= ? AND status = 'completed'
        GROUP BY DATE_TRUNC('month', order_date)
        ORDER BY month
        """,
        [store_id, cutoff, today],
    ).fetchall()

    if len(rows) < 2:
        return {"score": 50, "label": "Insufficient data", "detail": "Need at least 2 months of data"}

    revenues = [float(r[1]) for r in rows]
    n = len(revenues)
    x_vals = list(range(n))
    x_mean = sum(x_vals) / n
    y_mean = sum(revenues) / n

    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, revenues))
    denominator = sum((x - x_mean) ** 2 for x in x_vals)

    if denominator == 0 or y_mean == 0:
        return {"score": 50, "label": "Flat", "detail": "No meaningful revenue variation"}

    slope = numerator / denominator
    growth_rate = slope / y_mean

    score = int(min(100, max(0, 50 + growth_rate * 200)))

    if score >= 70:
        label = "Strong Growth"
    elif score >= 40:
        label = "Moderate"
    else:
        label = "Declining"

    detail = f"Monthly revenue trend: {growth_rate * 100:+.1f}% avg change"
    return {"score": score, "label": label, "detail": detail}


def _customer_loyalty(conn, store_id: str, cutoff: str, today: str) -> dict:
    """Weighted: returning_rate (40%) + avg orders per customer (30%) + repeat ratio (30%)."""
    row = conn.execute(
        """
        SELECT
            COUNT(DISTINCT customer_id) AS total,
            COUNT(DISTINCT CASE WHEN cnt > 1 THEN customer_id END) AS returning
        FROM (
            SELECT customer_id, COUNT(DISTINCT CAST(order_date AS DATE)) AS cnt
            FROM orders
            WHERE store_id = ? AND order_date >= ? AND order_date <= ? AND status = 'completed'
            GROUP BY customer_id
        ) sub
        """,
        [store_id, cutoff, today],
    ).fetchone()

    total = row[0] if row else 0
    returning = row[1] if row else 0
    returning_rate = (returning / total * 100) if total > 0 else 0

    agg = conn.execute(
        """
        SELECT AVG(order_count) AS avg_orders
        FROM (
            SELECT customer_id, COUNT(*) AS order_count
            FROM orders
            WHERE store_id = ? AND order_date >= ? AND order_date <= ? AND status = 'completed'
            GROUP BY customer_id
        ) sub
        """,
        [store_id, cutoff, today],
    ).fetchone()
    avg_orders = float(agg[0]) if agg and agg[0] else 1

    rate_score = min(100, returning_rate)
    orders_score = min(100, (avg_orders - 1) * 25)
    repeat_ratio_score = min(100, returning_rate * 1.2)

    score = int(rate_score * 0.4 + max(0, orders_score) * 0.3 + repeat_ratio_score * 0.3)
    score = min(100, max(0, score))

    if score >= 70:
        label = "Highly Loyal"
    elif score >= 40:
        label = "Moderate Loyalty"
    else:
        label = "Low Loyalty"

    detail = f"{returning_rate:.0f}% returning rate, {avg_orders:.1f} avg orders/customer"
    return {"score": score, "label": label, "detail": detail}


def _product_diversity(conn, store_id: str, cutoff: str, today: str) -> dict:
    """Inverse HHI on category revenue. 0 = single category, 100 = perfectly even."""
    rows = conn.execute(
        """
        SELECT
            COALESCE(category, 'Uncategorized') AS cat,
            SUM(total_price - discount_amount) AS rev
        FROM orders
        WHERE store_id = ? AND order_date >= ? AND order_date <= ? AND status = 'completed'
        GROUP BY COALESCE(category, 'Uncategorized')
        """,
        [store_id, cutoff, today],
    ).fetchall()

    if not rows or len(rows) < 1:
        return {"score": 0, "label": "No Data", "detail": "No category data available"}

    total = sum(float(r[1]) for r in rows)
    if total == 0:
        return {"score": 0, "label": "No Revenue", "detail": "Zero revenue in period"}

    shares = [float(r[1]) / total for r in rows]
    hhi = sum(s ** 2 for s in shares)

    n = len(rows)
    if n <= 1:
        score = 0
    else:
        min_hhi = 1.0 / n
        score = int((1 - (hhi - min_hhi) / (1 - min_hhi)) * 100) if hhi < 1 else 0

    score = min(100, max(0, score))

    if score >= 70:
        label = "Well Diversified"
    elif score >= 40:
        label = "Moderate"
    else:
        label = "Concentrated"

    detail = f"{n} categories, HHI={hhi:.3f}"
    return {"score": score, "label": label, "detail": detail}


def _revenue_stability(conn, store_id: str, cutoff: str, today: str) -> dict:
    """1 - coefficient_of_variation(weekly_revenue), clamped 0-100."""
    rows = conn.execute(
        """
        SELECT
            DATE_TRUNC('week', order_date) AS week,
            SUM(total_price - discount_amount) AS revenue
        FROM orders
        WHERE store_id = ? AND order_date >= ? AND order_date <= ? AND status = 'completed'
        GROUP BY DATE_TRUNC('week', order_date)
        ORDER BY week
        """,
        [store_id, cutoff, today],
    ).fetchall()

    if len(rows) < 3:
        return {"score": 50, "label": "Insufficient data", "detail": "Need 3+ weeks of data"}

    revenues = [float(r[1]) for r in rows]
    mean = sum(revenues) / len(revenues)
    if mean == 0:
        return {"score": 50, "label": "No Revenue", "detail": "Zero revenue"}

    variance = sum((x - mean) ** 2 for x in revenues) / len(revenues)
    std = math.sqrt(variance)
    cv = std / mean

    score = int(max(0, min(100, (1 - cv) * 100)))

    if score >= 70:
        label = "Highly Stable"
    elif score >= 40:
        label = "Moderate"
    else:
        label = "Volatile"

    detail = f"CV={cv:.2f}, weekly revenue std={_sym(store_id)}{std:,.0f}"
    return {"score": score, "label": label, "detail": detail}


def _discount_dependency(conn, store_id: str, cutoff: str, today: str) -> dict:
    """100 - (discount_ratio × 100). Low dependency = high score (good)."""
    row = conn.execute(
        """
        SELECT
            SUM(discount_amount) AS total_discount,
            SUM(total_price) AS total_revenue
        FROM orders
        WHERE store_id = ? AND order_date >= ? AND order_date <= ? AND status = 'completed'
        """,
        [store_id, cutoff, today],
    ).fetchone()

    total_discount = float(row[0]) if row and row[0] else 0
    total_revenue = float(row[1]) if row and row[1] else 0

    if total_revenue == 0:
        return {"score": 100, "label": "No Data", "detail": "No revenue data"}

    discount_ratio = total_discount / total_revenue
    score = int(max(0, min(100, (1 - discount_ratio) * 100)))

    if score >= 80:
        label = "Low Dependency"
    elif score >= 50:
        label = "Moderate"
    else:
        label = "High Dependency"

    detail = f"{discount_ratio * 100:.1f}% of revenue comes from discounted orders"
    return {"score": score, "label": label, "detail": detail}


def _seasonal_sensitivity(conn, store_id: str, cutoff: str, today: str) -> dict:
    """Inverse of monthly revenue share std dev. Low variance = high score."""
    rows = conn.execute(
        """
        SELECT
            DATE_TRUNC('month', order_date) AS month,
            SUM(total_price - discount_amount) AS revenue
        FROM orders
        WHERE store_id = ? AND order_date >= ? AND order_date <= ? AND status = 'completed'
        GROUP BY DATE_TRUNC('month', order_date)
        ORDER BY month
        """,
        [store_id, cutoff, today],
    ).fetchall()

    if len(rows) < 3:
        return {"score": 50, "label": "Insufficient data", "detail": "Need 3+ months"}

    revenues = [float(r[1]) for r in rows]
    total = sum(revenues)
    if total == 0:
        return {"score": 50, "label": "No Revenue", "detail": "Zero revenue"}

    shares = [r / total for r in revenues]
    expected_share = 1.0 / len(shares)
    variance = sum((s - expected_share) ** 2 for s in shares) / len(shares)
    std = math.sqrt(variance)

    score = int(max(0, min(100, (1 - std * 10) * 100)))

    if score >= 70:
        label = "Low Seasonality"
    elif score >= 40:
        label = "Moderate Seasonality"
    else:
        label = "Highly Seasonal"

    detail = f"Monthly revenue share std={std:.3f}, {len(rows)} months analyzed"
    return {"score": score, "label": label, "detail": detail}
