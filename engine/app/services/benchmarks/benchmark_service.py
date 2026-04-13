"""
Competitive benchmarks service — provides industry-average KPIs
for comparison against the user's actual store metrics.

Benchmarks are maintained as static lookup tables by industry vertical.
Real store KPIs are computed from DuckDB and compared against benchmarks.
"""

import logging

from app.core.database import get_duckdb_connection, get_sqlite_connection

logger = logging.getLogger(__name__)

# ── Industry benchmark data ─────────────────────────────────────
# Sources: industry reports, Shopify benchmarks, Statista averages.
# All values are monthly averages for a small/medium e-commerce business.

INDUSTRY_BENCHMARKS: dict[str, dict[str, float]] = {
    "fashion": {
        "aov": 65.0,
        "conversion_rate": 2.5,
        "repeat_purchase_rate": 25.0,
        "cart_abandonment_rate": 75.0,
        "avg_rating": 4.1,
        "return_rate": 30.0,
        "customer_lifetime_value": 180.0,
        "revenue_per_visitor": 1.60,
    },
    "electronics": {
        "aov": 120.0,
        "conversion_rate": 1.8,
        "repeat_purchase_rate": 15.0,
        "cart_abandonment_rate": 78.0,
        "avg_rating": 4.0,
        "return_rate": 15.0,
        "customer_lifetime_value": 250.0,
        "revenue_per_visitor": 2.10,
    },
    "beauty": {
        "aov": 50.0,
        "conversion_rate": 3.2,
        "repeat_purchase_rate": 35.0,
        "cart_abandonment_rate": 70.0,
        "avg_rating": 4.3,
        "return_rate": 10.0,
        "customer_lifetime_value": 200.0,
        "revenue_per_visitor": 1.55,
    },
    "food": {
        "aov": 35.0,
        "conversion_rate": 4.0,
        "repeat_purchase_rate": 45.0,
        "cart_abandonment_rate": 65.0,
        "avg_rating": 4.2,
        "return_rate": 3.0,
        "customer_lifetime_value": 150.0,
        "revenue_per_visitor": 1.40,
    },
    "home": {
        "aov": 95.0,
        "conversion_rate": 2.0,
        "repeat_purchase_rate": 20.0,
        "cart_abandonment_rate": 73.0,
        "avg_rating": 4.1,
        "return_rate": 20.0,
        "customer_lifetime_value": 220.0,
        "revenue_per_visitor": 1.90,
    },
    "sports": {
        "aov": 80.0,
        "conversion_rate": 2.2,
        "repeat_purchase_rate": 22.0,
        "cart_abandonment_rate": 72.0,
        "avg_rating": 4.2,
        "return_rate": 18.0,
        "customer_lifetime_value": 200.0,
        "revenue_per_visitor": 1.75,
    },
    "toys": {
        "aov": 45.0,
        "conversion_rate": 2.8,
        "repeat_purchase_rate": 20.0,
        "cart_abandonment_rate": 74.0,
        "avg_rating": 4.3,
        "return_rate": 12.0,
        "customer_lifetime_value": 120.0,
        "revenue_per_visitor": 1.25,
    },
    "jewelry": {
        "aov": 150.0,
        "conversion_rate": 1.5,
        "repeat_purchase_rate": 18.0,
        "cart_abandonment_rate": 80.0,
        "avg_rating": 4.4,
        "return_rate": 12.0,
        "customer_lifetime_value": 300.0,
        "revenue_per_visitor": 2.25,
    },
    "health": {
        "aov": 55.0,
        "conversion_rate": 3.5,
        "repeat_purchase_rate": 40.0,
        "cart_abandonment_rate": 68.0,
        "avg_rating": 4.2,
        "return_rate": 8.0,
        "customer_lifetime_value": 190.0,
        "revenue_per_visitor": 1.90,
    },
    "general": {
        "aov": 75.0,
        "conversion_rate": 2.5,
        "repeat_purchase_rate": 25.0,
        "cart_abandonment_rate": 73.0,
        "avg_rating": 4.1,
        "return_rate": 18.0,
        "customer_lifetime_value": 195.0,
        "revenue_per_visitor": 1.85,
    },
}

METRIC_LABELS = {
    "aov": "Avg. Order Value",
    "conversion_rate": "Conversion Rate (%)",
    "repeat_purchase_rate": "Repeat Purchase Rate (%)",
    "cart_abandonment_rate": "Cart Abandonment Rate (%)",
    "avg_rating": "Avg. Review Rating",
    "return_rate": "Return Rate (%)",
    "customer_lifetime_value": "Customer Lifetime Value",
    "revenue_per_visitor": "Revenue Per Visitor",
}

# Metrics where lower is better
_LOWER_IS_BETTER = {"cart_abandonment_rate", "return_rate"}


def _get_store_industry(store_id: str) -> str:
    conn = get_sqlite_connection()
    row = conn.execute(
        "SELECT industry FROM stores WHERE id = ?",
        (store_id,),
    ).fetchone()
    return (row[0] if row and row[0] else "general").lower()


def _compute_store_kpis(store_id: str) -> dict[str, float | None]:
    """Compute actual store KPIs from DuckDB to compare against benchmarks."""
    conn = get_duckdb_connection()

    kpis: dict[str, float | None] = {}

    # AOV
    row = conn.execute(
        "SELECT AVG(total_price) FROM orders WHERE store_id = ? AND status = 'completed'",
        [store_id],
    ).fetchone()
    kpis["aov"] = round(float(row[0]), 2) if row and row[0] else None

    # Repeat purchase rate
    row = conn.execute(
        """SELECT
             COUNT(DISTINCT CASE WHEN order_count > 1 THEN customer_id END) * 100.0
             / NULLIF(COUNT(DISTINCT customer_id), 0)
           FROM (
             SELECT customer_id, COUNT(*) as order_count
             FROM orders WHERE store_id = ? AND status = 'completed'
             GROUP BY customer_id
           )""",
        [store_id],
    ).fetchone()
    kpis["repeat_purchase_rate"] = round(float(row[0]), 1) if row and row[0] else None

    # Avg rating
    row = conn.execute(
        "SELECT AVG(rating) FROM reviews WHERE store_id = ? AND rating IS NOT NULL",
        [store_id],
    ).fetchone()
    kpis["avg_rating"] = round(float(row[0]), 2) if row and row[0] else None

    # CLV approximation: avg revenue per customer
    row = conn.execute(
        """SELECT AVG(total_rev) FROM (
             SELECT customer_id, SUM(total_price) as total_rev
             FROM orders WHERE store_id = ? AND status = 'completed'
             GROUP BY customer_id
           )""",
        [store_id],
    ).fetchone()
    kpis["customer_lifetime_value"] = round(float(row[0]), 2) if row and row[0] else None

    return kpis


def get_benchmarks(store_id: str) -> dict:
    """Compare store KPIs against industry benchmarks."""
    industry = _get_store_industry(store_id)
    benchmarks = INDUSTRY_BENCHMARKS.get(industry, INDUSTRY_BENCHMARKS["general"])
    store_kpis = _compute_store_kpis(store_id)

    comparisons = []
    for metric_key, bench_value in benchmarks.items():
        store_value = store_kpis.get(metric_key)
        lower_better = metric_key in _LOWER_IS_BETTER

        if store_value is not None:
            diff = store_value - bench_value
            if lower_better:
                status = "above" if diff < -1 else ("below" if diff > 1 else "on_par")
            else:
                status = "above" if diff > 1 else ("below" if diff < -1 else "on_par")
            diff_pct = round(diff / bench_value * 100, 1) if bench_value else 0.0
        else:
            diff = None
            diff_pct = None
            status = "no_data"

        comparisons.append({
            "metric": metric_key,
            "label": METRIC_LABELS.get(metric_key, metric_key),
            "benchmark": bench_value,
            "store_value": store_value,
            "difference": round(diff, 2) if diff is not None else None,
            "difference_pct": diff_pct,
            "status": status,
            "lower_is_better": lower_better,
        })

    return {
        "industry": industry,
        "comparisons": comparisons,
        "available_industries": sorted(INDUSTRY_BENCHMARKS.keys()),
    }


def get_benchmark_for_industry(industry: str) -> dict:
    """Get raw benchmark values for a given industry."""
    industry = industry.lower()
    benchmarks = INDUSTRY_BENCHMARKS.get(industry)
    if not benchmarks:
        return {"error": f"Unknown industry: {industry}"}

    return {
        "industry": industry,
        "metrics": [
            {
                "metric": k,
                "label": METRIC_LABELS.get(k, k),
                "value": v,
                "lower_is_better": k in _LOWER_IS_BETTER,
            }
            for k, v in benchmarks.items()
        ],
    }
