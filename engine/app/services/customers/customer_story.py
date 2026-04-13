"""
Customer Story Generator — creates plain-language narratives about
individual customer journeys and behavior patterns.
"""

import logging
from datetime import datetime, timedelta, timezone

from app.core.database import get_duckdb_connection
from app.services.currency.currency_helper import sym as _sym

logger = logging.getLogger(__name__)


def generate_customer_story(store_id: str, customer_id: str) -> dict:
    """Build a narrative story about a specific customer's journey."""
    conn = get_duckdb_connection()

    # Core customer stats
    stats = conn.execute(
        """SELECT
             customer_id,
             MIN(order_date) as first_order,
             MAX(order_date) as last_order,
             COUNT(DISTINCT order_id) as total_orders,
             SUM(total_price - discount_amount) as total_spend,
             AVG(total_price - discount_amount) as avg_order,
             COUNT(DISTINCT category) as categories_bought,
             COUNT(DISTINCT channel) as channels_used
           FROM orders
           WHERE store_id = ? AND customer_id = ?
           GROUP BY customer_id""",
        [store_id, customer_id],
    ).fetchone()

    if not stats:
        return {
            "customer_id": customer_id,
            "story": "No order history found for this customer.",
            "segments": [],
            "metrics": {},
            "timeline": [],
        }

    cid = str(stats[0])
    first_order = str(stats[1])[:10]
    last_order = str(stats[2])[:10]
    total_orders = int(stats[3])
    total_spend = float(stats[4])
    avg_order = float(stats[5])
    categories = int(stats[6])
    channels = int(stats[7])

    # Determine tenure
    first_dt = datetime.fromisoformat(first_order)
    last_dt = datetime.fromisoformat(last_order)
    tenure_days = (last_dt - first_dt).days
    now = datetime.now(timezone.utc).date()
    days_since_last = (now - last_dt.date()).days

    # Top products
    top_products = conn.execute(
        """SELECT product_name, COUNT(*) as cnt, SUM(total_price - discount_amount) as rev
           FROM orders WHERE store_id = ? AND customer_id = ? AND product_name IS NOT NULL
           GROUP BY product_name ORDER BY rev DESC LIMIT 3""",
        [store_id, customer_id],
    ).fetchall()

    # Top categories
    top_categories = conn.execute(
        """SELECT category, COUNT(*) as cnt, SUM(total_price - discount_amount) as rev
           FROM orders WHERE store_id = ? AND customer_id = ? AND category IS NOT NULL
           GROUP BY category ORDER BY rev DESC LIMIT 3""",
        [store_id, customer_id],
    ).fetchall()

    # Order timeline (monthly)
    timeline = conn.execute(
        """SELECT
             DATE_TRUNC('month', order_date::DATE) as month,
             COUNT(DISTINCT order_id) as orders,
             SUM(total_price - discount_amount) as revenue
           FROM orders WHERE store_id = ? AND customer_id = ?
           GROUP BY month ORDER BY month""",
        [store_id, customer_id],
    ).fetchall()

    # Build segments
    segments: list[str] = []
    if total_orders >= 5:
        segments.append("loyal")
    elif total_orders >= 2:
        segments.append("repeat")
    else:
        segments.append("one-time")

    if total_spend > 500:
        segments.append("high-value")
    elif total_spend > 100:
        segments.append("mid-value")

    if days_since_last > 90:
        segments.append("at-risk")
    elif days_since_last <= 30:
        segments.append("active")

    # Build narrative
    parts = []
    parts.append(f"This customer first purchased on {first_order} and has placed {total_orders} order{'s' if total_orders != 1 else ''} totaling {_sym(store_id)}{total_spend:,.0f}.")

    if tenure_days > 30:
        parts.append(f"Their relationship spans {tenure_days} days with an average order of {_sym(store_id)}{avg_order:,.0f}.")

    if top_products:
        favs = ", ".join(str(p[0]) for p in top_products[:2])
        parts.append(f"Their favorite products include {favs}.")

    if categories > 1:
        parts.append(f"They shop across {categories} categories.")

    if days_since_last > 90:
        parts.append(f"They haven't purchased in {days_since_last} days — they may be at risk of churning.")
    elif days_since_last <= 7:
        parts.append("They purchased very recently and are actively engaged.")

    # Refund history
    refund_row = conn.execute(
        """SELECT COUNT(*), COALESCE(SUM(refund_amount), 0)
           FROM orders WHERE store_id = ? AND customer_id = ? AND status = 'refunded'""",
        [store_id, customer_id],
    ).fetchone()
    if refund_row and int(refund_row[0]) > 0:
        parts.append(f"They have {int(refund_row[0])} refund(s) totaling {_sym(store_id)}{float(refund_row[1]):,.0f}.")

    return {
        "customer_id": cid,
        "story": " ".join(parts),
        "segments": segments,
        "metrics": {
            "total_orders": total_orders,
            "total_spend": round(total_spend, 2),
            "avg_order_value": round(avg_order, 2),
            "first_order": first_order,
            "last_order": last_order,
            "tenure_days": tenure_days,
            "days_since_last": days_since_last,
            "categories_bought": categories,
            "channels_used": channels,
        },
        "top_products": [
            {"name": str(p[0]), "orders": int(p[1]), "revenue": round(float(p[2]), 2)}
            for p in top_products
        ],
        "top_categories": [
            {"name": str(c[0]), "orders": int(c[1]), "revenue": round(float(c[2]), 2)}
            for c in top_categories
        ],
        "timeline": [
            {"month": str(t[0])[:7], "orders": int(t[1]), "revenue": round(float(t[2]), 2)}
            for t in timeline
        ],
    }
