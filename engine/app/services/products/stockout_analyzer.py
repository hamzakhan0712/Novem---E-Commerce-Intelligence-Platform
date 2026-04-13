"""
Stockout analyzer — Detect past stockout events and estimate revenue loss.
"""

import logging
from datetime import datetime, timedelta, timezone

from app.core.database import get_duckdb_connection

logger = logging.getLogger(__name__)


def analyze_stockout_impact(store_id: str, period: str = "90d") -> dict:
    """Find products that went to 0 stock and estimate missed revenue."""
    conn = get_duckdb_connection()
    days = int(period[:-1]) * 30 if period.endswith("m") else int(period.rstrip("d"))
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start = (now - timedelta(days=days)).strftime("%Y-%m-%d")

    # Get stock snapshots with zero quantity in the period
    stockout_df = conn.execute(
        """
        SELECT
            s.product_id,
            p.product_name,
            p.category,
            s.snapshot_date
        FROM stock_levels s
        LEFT JOIN products p ON s.product_id = p.product_id AND s.store_id = p.store_id
        WHERE s.store_id = ?
          AND s.snapshot_date >= ?
          AND s.quantity_on_hand = 0
        ORDER BY s.product_id, s.snapshot_date
        """,
        [store_id, start],
    ).fetchdf()

    if stockout_df.empty:
        return {
            "events": [],
            "total_estimated_loss": 0.0,
            "total_stockout_days": 0,
            "products_affected": 0,
            "period": period,
            "message": "No stockout events detected in this period.",
        }

    # Average daily revenue per product (from orders before the period for baseline)
    baseline_start = (now - timedelta(days=days * 2)).strftime("%Y-%m-%d")
    revenue_df = conn.execute(
        """
        SELECT
            product_id,
            SUM(total_price - discount_amount) * 1.0 /
                GREATEST(DATEDIFF('day', MIN(CAST(order_date AS DATE)), MAX(CAST(order_date AS DATE))), 1)
                AS avg_daily_revenue
        FROM orders
        WHERE store_id = ?
          AND order_date >= ?
          AND order_date <= ?
          AND status = 'completed'
          AND product_id IS NOT NULL
        GROUP BY product_id
        """,
        [store_id, baseline_start, start],
    ).fetchdf()

    revenue_map = {}
    if not revenue_df.empty:
        revenue_map = dict(zip(
            revenue_df["product_id"].astype(str),
            revenue_df["avg_daily_revenue"].astype(float),
        ))

    # Group consecutive stockout snapshots into events
    # Stock snapshots are weekly, so each snapshot = ~7 days of stockout
    events = []
    for pid, group in stockout_df.groupby("product_id"):
        pid_str = str(pid)
        product_name = group["product_name"].iloc[0] or pid_str
        category = group["category"].iloc[0] or "Uncategorized"
        dates = sorted(group["snapshot_date"].tolist())

        avg_daily_rev = revenue_map.get(pid_str, 0.0)

        # Each snapshot represents ~7 days (weekly snapshots)
        stockout_days = len(dates) * 7
        estimated_loss = round(avg_daily_rev * stockout_days, 2)

        events.append({
            "product_id": pid_str,
            "product_name": product_name,
            "category": category,
            "stockout_snapshots": len(dates),
            "stockout_start": str(dates[0]),
            "stockout_end": str(dates[-1]),
            "stockout_days": stockout_days,
            "avg_daily_revenue": round(avg_daily_rev, 2),
            "estimated_missed_revenue": estimated_loss,
        })

    events.sort(key=lambda e: e["estimated_missed_revenue"], reverse=True)

    total_loss = sum(e["estimated_missed_revenue"] for e in events)
    total_days = sum(e["stockout_days"] for e in events)

    return {
        "events": events,
        "total_estimated_loss": round(total_loss, 2),
        "total_stockout_days": total_days,
        "products_affected": len(events),
        "period": period,
    }
