"""
What-If scenario simulator — lets users adjust business levers and see projected impact.

Uses the existing KPI baseline + revenue decomposition formulas to project outcomes.
Elasticity values are estimated from the store's own historical data when possible,
otherwise industry-average defaults are used (clearly labeled as estimates).
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

# Industry-average defaults — used only when store data is insufficient
_DEFAULT_PRICE_ELASTICITY = -0.3
_DEFAULT_NEW_CUSTOMER_AOV_RATIO = 0.7
_DEFAULT_CHANNEL_UPLIFT = 0.08
_DEFAULT_DISCOUNT_ELASTICITY = -0.1


def _estimate_price_elasticity(store_id: str) -> tuple[float, bool]:
    """Try to estimate price elasticity from the store's own AOV and order volume history.

    Returns (elasticity, is_data_driven). If insufficient data, returns the
    industry-average default with is_data_driven=False.
    """
    conn = get_duckdb_connection()
    try:
        rows = conn.execute(
            """SELECT strftime(order_date, '%Y-%m') AS month,
                      AVG(total_price - discount_amount) AS avg_aov,
                      COUNT(*) AS order_count
               FROM orders
               WHERE store_id = ? AND status = 'completed'
               GROUP BY month
               HAVING COUNT(*) >= 5
               ORDER BY month""",
            [store_id],
        ).fetchall()
        if len(rows) < 4:
            return _DEFAULT_PRICE_ELASTICITY, False

        # Compute month-over-month % changes in AOV and order volume
        aov_changes = []
        vol_changes = []
        for i in range(1, len(rows)):
            prev_aov, curr_aov = float(rows[i - 1][1]), float(rows[i][1])
            prev_vol, curr_vol = int(rows[i - 1][2]), int(rows[i][2])
            if prev_aov > 0 and prev_vol > 0:
                aov_changes.append((curr_aov - prev_aov) / prev_aov * 100)
                vol_changes.append((curr_vol - prev_vol) / prev_vol * 100)

        if len(aov_changes) < 3:
            return _DEFAULT_PRICE_ELASTICITY, False

        # Simple regression: elasticity ≈ avg(Δvolume / Δprice) for months where price changed
        pairs = [(a, v) for a, v in zip(aov_changes, vol_changes) if abs(a) > 1.0]
        if len(pairs) < 2:
            return _DEFAULT_PRICE_ELASTICITY, False

        elasticities = [v / a for a, v in pairs if abs(a) > 0]
        avg_elast = sum(elasticities) / len(elasticities)
        # Clamp to reasonable range
        clamped = max(-2.0, min(0.0, avg_elast))
        return round(clamped, 2), True
    except Exception:
        return _DEFAULT_PRICE_ELASTICITY, False


def _estimate_new_customer_aov_ratio(store_id: str) -> tuple[float, bool]:
    """Estimate the ratio of first-order AOV to overall AOV from historical data."""
    conn = get_duckdb_connection()
    try:
        row = conn.execute(
            """WITH first_orders AS (
                 SELECT customer_id, MIN(order_date) AS first_date
                 FROM orders WHERE store_id = ? AND status = 'completed'
                 GROUP BY customer_id
               )
               SELECT
                 AVG(CASE WHEN o.order_date = f.first_date THEN o.total_price - o.discount_amount END) AS first_aov,
                 AVG(o.total_price - o.discount_amount) AS overall_aov
               FROM orders o
               JOIN first_orders f ON o.customer_id = f.customer_id
               WHERE o.store_id = ? AND o.status = 'completed'""",
            [store_id, store_id],
        ).fetchone()
        if row and row[0] and row[1] and float(row[1]) > 0:
            ratio = float(row[0]) / float(row[1])
            clamped = max(0.3, min(1.5, round(ratio, 2)))
            return clamped, True
    except Exception:
        pass
    return _DEFAULT_NEW_CUSTOMER_AOV_RATIO, False


def run_scenario(store_id: str, period: str = "30d", adjustments: dict | None = None) -> dict:
    """
    Run what-if simulation with the given adjustments.

    Adjustments dict can contain:
      price_change_pct:    e.g. 10  → increase all prices by 10%
      order_volume_change_pct: e.g. -5  → 5% fewer orders
      refund_rate_target_pct:  e.g. 3   → reduce refund rate to 3%
      new_customer_change_pct: e.g. 15  → 15% more new customers
      discount_change_pct:     e.g. -20 → reduce discounts by 20%
      channel_count_change:    e.g. 1   → add 1 new channel
    """
    if adjustments is None:
        adjustments = {}

    kpis = calculate_kpis(store_id, period)
    if not kpis or not kpis.get("current"):
        return {
            "baseline": {},
            "projected": {},
            "adjustments": adjustments,
            "impacts": [],
            "message": "Insufficient data to run simulation.",
        }

    current = kpis["current"]
    base_revenue = float(current.get("revenue", 0))
    base_orders = int(current.get("order_count", current.get("orders", 0)))
    base_customers = int(current.get("unique_customers", current.get("customers", 0)))
    base_aov = float(current.get("aov", 0))

    if base_revenue == 0:
        return {
            "baseline": current,
            "projected": current,
            "adjustments": adjustments,
            "impacts": [],
            "message": "No revenue in the selected period.",
        }

    # Fetch additional baseline data
    conn = get_duckdb_connection()
    days = _PERIOD_DAYS.get(period, 30)
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=days)).strftime("%Y-%m-%d")

    refund_row = conn.execute(
        """
        SELECT
            SUM(refund_amount) AS total_refunds,
            SUM(discount_amount) AS total_discounts
        FROM orders
        WHERE store_id = ? AND order_date >= ? AND status = 'completed'
        """,
        [store_id, start],
    ).fetchone()

    base_refunds = float(refund_row[0] or 0) if refund_row else 0.0
    base_discounts = float(refund_row[1] or 0) if refund_row else 0.0
    base_refund_rate = (base_refunds / base_revenue * 100) if base_revenue > 0 else 0

    # Compute per-adjustment impacts
    impacts = []
    proj_revenue = base_revenue
    proj_orders = base_orders
    proj_customers = base_customers
    proj_aov = base_aov

    # Track which parameters are data-driven vs estimated
    assumptions: list[str] = []

    # 1. Price change
    price_pct = float(adjustments.get("price_change_pct", 0))
    if price_pct != 0:
        elasticity, elast_is_data = _estimate_price_elasticity(store_id)
        if elast_is_data:
            assumptions.append(f"Price elasticity ({elasticity}) estimated from your store's historical AOV/volume patterns")
        else:
            assumptions.append(f"Price elasticity ({elasticity}) is an industry-average estimate — your actual results may differ")
        demand_change = price_pct * elasticity  # if price +10%, demand change % = 10 * elasticity
        new_aov = base_aov * (1 + price_pct / 100)
        new_orders = base_orders * (1 + demand_change / 100)
        revenue_impact = (new_aov * new_orders) - base_revenue
        proj_aov = new_aov
        proj_orders = int(new_orders)
        proj_revenue += revenue_impact
        source_label = "data-driven" if elast_is_data else "estimated"
        impacts.append({
            "lever": "Price Change",
            "adjustment": f"{price_pct:+.1f}%",
            "revenue_impact": round(revenue_impact, 2),
            "detail": f"AOV {base_aov:.2f} → {new_aov:.2f}, orders {base_orders} → {int(new_orders)} (elasticity {elasticity}, {source_label})",
        })

    # 2. Order volume change
    vol_pct = float(adjustments.get("order_volume_change_pct", 0))
    if vol_pct != 0:
        order_delta = base_orders * (vol_pct / 100)
        revenue_impact = order_delta * proj_aov
        proj_orders = int(proj_orders + order_delta)
        proj_revenue += revenue_impact
        impacts.append({
            "lever": "Order Volume",
            "adjustment": f"{vol_pct:+.1f}%",
            "revenue_impact": round(revenue_impact, 2),
            "detail": f"{int(order_delta):+d} orders × {proj_aov:.2f} AOV",
        })

    # 3. Refund rate reduction
    refund_target = adjustments.get("refund_rate_target_pct")
    if refund_target is not None:
        refund_target = float(refund_target)
        if refund_target < base_refund_rate:
            refund_savings = base_revenue * (base_refund_rate - refund_target) / 100
            proj_revenue += refund_savings
            impacts.append({
                "lever": "Refund Rate Reduction",
                "adjustment": f"{base_refund_rate:.1f}% → {refund_target:.1f}%",
                "revenue_impact": round(refund_savings, 2),
                "detail": f"Saving {refund_savings:.2f} in refunds",
            })

    # 4. New customer acquisition
    cust_pct = float(adjustments.get("new_customer_change_pct", 0))
    if cust_pct != 0:
        cust_delta = base_customers * (cust_pct / 100)
        aov_ratio, ratio_is_data = _estimate_new_customer_aov_ratio(store_id)
        if ratio_is_data:
            assumptions.append(f"New customer AOV ratio ({aov_ratio}×) calculated from your first-order data")
        else:
            assumptions.append(f"New customer AOV ratio ({aov_ratio}×) is an industry-average estimate")
        revenue_impact = cust_delta * proj_aov * aov_ratio
        proj_customers = int(proj_customers + cust_delta)
        proj_revenue += revenue_impact
        source_label = "data-driven" if ratio_is_data else "estimated"
        impacts.append({
            "lever": "Customer Acquisition",
            "adjustment": f"{cust_pct:+.1f}%",
            "revenue_impact": round(revenue_impact, 2),
            "detail": f"{int(cust_delta):+d} new customers × {proj_aov * aov_ratio:.2f} avg first-order value ({source_label})",
        })

    # 5. Discount reduction
    disc_pct = float(adjustments.get("discount_change_pct", 0))
    if disc_pct != 0:
        discount_delta = base_discounts * (disc_pct / 100)
        # Reducing discounts recovers margin but may lose some orders
        lost_orders = abs(discount_delta / proj_aov) * abs(_DEFAULT_DISCOUNT_ELASTICITY) if disc_pct < 0 else 0
        revenue_impact = -discount_delta - (lost_orders * proj_aov)
        proj_revenue += revenue_impact
        assumptions.append(f"Discount elasticity ({_DEFAULT_DISCOUNT_ELASTICITY}) is an industry-average estimate")
        impacts.append({
            "lever": "Discount Strategy",
            "adjustment": f"{disc_pct:+.1f}% discount spend",
            "revenue_impact": round(revenue_impact, 2),
            "detail": f"Discount change: {discount_delta:+.2f}, est. order loss: {lost_orders:.0f}",
        })

    # 6. Channel expansion
    chan_change = int(adjustments.get("channel_count_change", 0))
    if chan_change > 0:
        uplift = base_revenue * _DEFAULT_CHANNEL_UPLIFT * chan_change
        proj_revenue += uplift
        assumptions.append(f"Channel uplift ({_DEFAULT_CHANNEL_UPLIFT * 100:.0f}% per channel) is an industry-average estimate")
        impacts.append({
            "lever": "Channel Expansion",
            "adjustment": f"+{chan_change} channel(s)",
            "revenue_impact": round(uplift, 2),
            "detail": f"Each new channel adds ~{_DEFAULT_CHANNEL_UPLIFT * 100:.0f}% revenue uplift ({uplift:.2f})",
        })

    # Projected state
    proj_aov_final = proj_revenue / proj_orders if proj_orders > 0 else 0
    total_impact = proj_revenue - base_revenue
    impact_pct = (total_impact / base_revenue * 100) if base_revenue > 0 else 0

    projected = {
        "revenue": round(proj_revenue, 2),
        "orders": proj_orders,
        "customers": proj_customers,
        "aov": round(proj_aov_final, 2),
    }

    return {
        "baseline": {
            "revenue": round(base_revenue, 2),
            "orders": base_orders,
            "customers": base_customers,
            "aov": round(base_aov, 2),
            "refund_rate": round(base_refund_rate, 2),
            "total_discounts": round(base_discounts, 2),
        },
        "projected": projected,
        "total_impact": round(total_impact, 2),
        "impact_pct": round(impact_pct, 2),
        "adjustments": adjustments,
        "impacts": impacts,
        "period": period,
        "assumptions": assumptions,
        "disclaimer": (
            "Projections are estimates based on historical store data where available "
            "and industry-average benchmarks otherwise. Actual results will vary based on "
            "market conditions, competition, and execution."
        ),
    }
