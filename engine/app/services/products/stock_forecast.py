"""
Stock forecast — Project when each product will run out of stock.
"""

import logging
from datetime import datetime, timedelta, timezone

from app.core.database import get_duckdb_connection

logger = logging.getLogger(__name__)


def forecast_stock_levels(store_id: str, period: str = "90d") -> dict:
    """Forecast stock depletion for each product based on recent demand."""
    conn = get_duckdb_connection()
    days = int(period[:-1]) * 30 if period.endswith("m") else int(period.rstrip("d"))
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    today = now.strftime("%Y-%m-%d")

    # Average daily demand from orders
    demand_df = conn.execute(
        """
        SELECT
            o.product_id,
            o.product_name,
            p.category,
            SUM(o.quantity)                       AS total_units,
            COUNT(DISTINCT CAST(o.order_date AS DATE)) AS selling_days,
            SUM(o.quantity) * 1.0 / GREATEST(DATEDIFF('day',
                MIN(CAST(o.order_date AS DATE)),
                MAX(CAST(o.order_date AS DATE))
            ), 1)                                  AS avg_daily_demand
        FROM orders o
        LEFT JOIN products p ON o.product_id = p.product_id AND o.store_id = p.store_id
        WHERE o.store_id = ?
          AND o.order_date >= ?
          AND o.status = 'completed'
          AND o.product_id IS NOT NULL
        GROUP BY o.product_id, o.product_name, p.category
        """,
        [store_id, start],
    ).fetchdf()

    if demand_df.empty:
        return {
            "products": [],
            "summary": _empty_summary(),
            "period": period,
            "message": "No order data for stock forecasting.",
        }

    # Latest stock snapshot per product
    stock_df = conn.execute(
        """
        SELECT product_id, quantity_on_hand
        FROM stock_levels
        WHERE store_id = ?
          AND snapshot_date = (SELECT MAX(snapshot_date) FROM stock_levels WHERE store_id = ?)
        """,
        [store_id, store_id],
    ).fetchdf()

    stock_map = {}
    if not stock_df.empty:
        stock_map = dict(zip(
            stock_df["product_id"].astype(str),
            stock_df["quantity_on_hand"].astype(int),
        ))

    products = []
    for _, row in demand_df.iterrows():
        pid = str(row["product_id"])
        avg_demand = float(row["avg_daily_demand"])
        current_stock = stock_map.get(pid, 0)

        if avg_demand > 0 and current_stock > 0:
            days_left = current_stock / avg_demand
            stockout_date = (now + timedelta(days=days_left)).strftime("%Y-%m-%d")
        elif current_stock == 0:
            days_left = 0
            stockout_date = today
        else:
            days_left = 999
            stockout_date = None

        if days_left <= 7:
            urgency = "stockout_imminent"
        elif days_left <= 14:
            urgency = "low_stock"
        elif days_left <= 30:
            urgency = "adequate"
        else:
            urgency = "well_stocked"

        products.append({
            "product_id": pid,
            "product_name": row["product_name"],
            "category": row["category"] or "Uncategorized",
            "current_stock": current_stock,
            "avg_daily_demand": round(avg_demand, 2),
            "days_until_stockout": round(days_left, 1),
            "predicted_stockout_date": stockout_date,
            "urgency": urgency,
        })

    # Sort by urgency (most critical first)
    urgency_order = {"stockout_imminent": 0, "low_stock": 1, "adequate": 2, "well_stocked": 3}
    products.sort(key=lambda p: (urgency_order.get(p["urgency"], 4), p["days_until_stockout"]))

    summary = {
        "total_products": len(products),
        "stockout_imminent": sum(1 for p in products if p["urgency"] == "stockout_imminent"),
        "low_stock": sum(1 for p in products if p["urgency"] == "low_stock"),
        "adequate": sum(1 for p in products if p["urgency"] == "adequate"),
        "well_stocked": sum(1 for p in products if p["urgency"] == "well_stocked"),
    }

    return {
        "products": products,
        "summary": summary,
        "period": period,
    }


def _empty_summary() -> dict:
    return {
        "total_products": 0,
        "stockout_imminent": 0,
        "low_stock": 0,
        "adequate": 0,
        "well_stocked": 0,
    }
