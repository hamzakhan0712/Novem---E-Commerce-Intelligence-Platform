"""
Missed revenue detector — identifies quantified revenue leaks (refunds,
churned customers, potential stockouts).
"""

import logging
from datetime import datetime, timedelta, timezone

from app.core.database import get_duckdb_connection
from app.services.dashboard.kpi_calculator import calculate_kpis
from app.services.currency.currency_helper import sym as _sym

logger = logging.getLogger(__name__)

_PERIOD_DAYS = {
    "7d": 7, "14d": 14, "30d": 30, "60d": 60, "90d": 90,
    "6m": 182, "12m": 365,
}


def _period_start(period: str) -> str:
    days = _PERIOD_DAYS.get(period, 30)
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")


def detect_missed_revenue(store_id: str, period: str = "30d") -> dict:
    """Return a summary of missed revenue opportunities, broken into categories."""
    conn = get_duckdb_connection()
    start_date = _period_start(period)

    refund_loss = _refund_losses(conn, store_id, start_date)
    churn_loss = _churn_losses(conn, store_id, start_date)
    stockout_loss = _stockout_losses(conn, store_id, start_date, period)

    opportunities = []
    if refund_loss["items"]:
        opportunities.extend(refund_loss["items"])
    if churn_loss["items"]:
        opportunities.extend(churn_loss["items"])
    if stockout_loss["items"]:
        opportunities.extend(stockout_loss["items"])

    opportunities.sort(key=lambda x: x.get("amount", 0), reverse=True)

    total = refund_loss["total"] + churn_loss["total"] + stockout_loss["total"]

    return {
        "total_missed_revenue": round(total, 2),
        "breakdown": {
            "refunds": {
                "total": refund_loss["total"],
                "count": len(refund_loss["items"]),
                "items": refund_loss["items"][:10],
            },
            "churned_customers": {
                "total": churn_loss["total"],
                "count": len(churn_loss["items"]),
                "items": churn_loss["items"][:10],
            },
            "stockout_signals": {
                "total": stockout_loss["total"],
                "count": len(stockout_loss["items"]),
                "items": stockout_loss["items"][:10],
            },
        },
        "opportunities": opportunities[:15],
        "period": period,
    }


def _refund_losses(conn, store_id: str, start_date: str) -> dict:
    """Quantify revenue lost to refunds, broken down by reason/product."""
    rows = conn.execute(
        """SELECT
             COALESCE(product_name, 'Unknown') as product,
             COALESCE(refund_reason, 'Not specified') as reason,
             COUNT(*) as cnt,
             COALESCE(SUM(refund_amount), 0) as total_refund,
             COALESCE(SUM(total_price - discount_amount), 0) as total_order_value
           FROM orders
           WHERE store_id = ? AND order_date >= ? AND status = 'refunded'
           GROUP BY product, reason
           ORDER BY total_refund DESC
           LIMIT 20""",
        [store_id, start_date],
    ).fetchall()

    items = []
    total = 0.0
    for r in rows:
        amount = float(r[3])
        total += amount
        items.append({
            "type": "refund",
            "product": str(r[0]),
            "reason": str(r[1]),
            "count": int(r[2]),
            "amount": round(amount, 2),
            "description": f"{r[0]}: {int(r[2])} refunds ({_sym(store_id)}{amount:,.0f}) — reason: {r[1]}",
        })

    return {"total": round(total, 2), "items": items}


def _churn_losses(conn, store_id: str, start_date: str) -> dict:
    """Estimate revenue lost from churned repeat customers."""
    rows = conn.execute(
        """WITH customer_stats AS (
             SELECT
               customer_id,
               COUNT(DISTINCT order_id) as total_orders,
               SUM(total_price - discount_amount) as lifetime_spend,
               MAX(order_date) as last_order,
               AVG(total_price) as avg_order_value
             FROM orders WHERE store_id = ? AND status = 'completed'
             GROUP BY customer_id
             HAVING total_orders >= 2
           )
           SELECT
             customer_id,
             total_orders,
             lifetime_spend,
             last_order,
             avg_order_value
           FROM customer_stats
           WHERE last_order < ?
           ORDER BY lifetime_spend DESC
           LIMIT 20""",
        [store_id, start_date],
    ).fetchall()

    items = []
    total = 0.0
    for r in rows:
        avg_val = float(r[4])
        # Estimate: they would have placed ~1 order per period
        projected = avg_val
        total += projected
        items.append({
            "type": "churn",
            "customer_id": str(r[0]),
            "total_orders": int(r[1]),
            "lifetime_spend": round(float(r[2]), 2),
            "last_order": str(r[3]),
            "amount": round(projected, 2),
            "description": f"Customer with {int(r[1])} orders ({_sym(store_id)}{float(r[2]):,.0f} lifetime) hasn't purchased since {str(r[3])[:10]}. Est. missed: {_sym(store_id)}{projected:,.0f}",
        })

    return {"total": round(total, 2), "items": items}


def _stockout_losses(conn, store_id: str, start_date: str, period: str) -> dict:
    """
    Detect potential stockout losses via order-gap heuristic:
    products that suddenly stopped selling mid-period despite prior sales velocity.
    """
    days = _PERIOD_DAYS.get(period, 30)
    midpoint = (datetime.now(timezone.utc) - timedelta(days=days // 2)).strftime("%Y-%m-%d")

    rows = conn.execute(
        """WITH first_half AS (
             SELECT product_name,
                    COUNT(DISTINCT order_id) as orders_first,
                    SUM(total_price - discount_amount) as rev_first
             FROM orders
             WHERE store_id = ? AND order_date >= ? AND order_date < ?
               AND product_name IS NOT NULL AND status = 'completed'
             GROUP BY product_name
           ),
           second_half AS (
             SELECT product_name,
                    COUNT(DISTINCT order_id) as orders_second,
                    SUM(total_price - discount_amount) as rev_second
             FROM orders
             WHERE store_id = ? AND order_date >= ?
               AND product_name IS NOT NULL AND status = 'completed'
             GROUP BY product_name
           )
           SELECT
             f.product_name,
             f.orders_first,
             f.rev_first,
             COALESCE(s.orders_second, 0) as orders_second,
             COALESCE(s.rev_second, 0) as rev_second
           FROM first_half f
           LEFT JOIN second_half s ON f.product_name = s.product_name
           WHERE f.orders_first >= 3
             AND COALESCE(s.orders_second, 0) <= f.orders_first * 0.2
           ORDER BY f.rev_first DESC
           LIMIT 10""",
        [store_id, start_date, midpoint, store_id, midpoint],
    ).fetchall()

    items = []
    total = 0.0
    for r in rows:
        product = str(r[0])
        first_rev = float(r[2])
        second_rev = float(r[4])
        missed = first_rev - second_rev
        if missed <= 0:
            continue
        total += missed
        items.append({
            "type": "stockout",
            "product": product,
            "first_half_orders": int(r[1]),
            "second_half_orders": int(r[3]),
            "amount": round(missed, 2),
            "description": f"{product}: sold {int(r[1])} orders in first half but only {int(r[3])} in second half. Potential missed revenue: {_sym(store_id)}{missed:,.0f}",
        })

    return {"total": round(total, 2), "items": items}
