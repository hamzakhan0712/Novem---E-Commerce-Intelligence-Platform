"""
Inventory optimization — reorder point, safety stock, and demand forecasting.

Uses historical order velocity + lead time to compute optimal stock levels.
"""

import logging
import math
from datetime import datetime, timedelta, timezone

from app.core.database import get_duckdb_connection

logger = logging.getLogger(__name__)


def get_inventory_analysis(store_id: str, period: str = "90d", service_level: float = 0.95) -> dict:
    """
    Analyze inventory and compute reorder points for each product.

    Uses:
      - Average daily demand from orders
      - Demand variability (std dev of daily sales)
      - Lead time from stock_levels table (or default 7 days)
      - Safety stock = Z × σ_demand × √lead_time
      - Reorder point = (avg_daily_demand × lead_time) + safety_stock
    """
    conn = get_duckdb_connection()
    days = int(period[:-1]) * 30 if period.endswith("m") else int(period.rstrip("d"))
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=days)).strftime("%Y-%m-%d")

    # Daily demand per product
    demand_df = conn.execute(
        """
        SELECT
            product_id,
            product_name,
            category,
            CAST(order_date AS DATE) AS sale_date,
            SUM(quantity)            AS daily_units
        FROM orders
        WHERE store_id = ?
          AND order_date >= ?
          AND status = 'completed'
          AND product_id IS NOT NULL
        GROUP BY product_id, product_name, category, sale_date
        ORDER BY product_id, sale_date
        """,
        [store_id, start],
    ).fetchdf()

    if demand_df.empty:
        return {
            "products": [],
            "summary": {
                "total_products": 0,
                "needs_reorder": 0,
                "overstocked": 0,
                "healthy": 0,
                "no_stock_data": 0,
            },
            "service_level": service_level,
            "message": "No order data for inventory analysis.",
        }

    # Current stock levels (latest snapshot per product)
    stock_df = conn.execute(
        """
        SELECT product_id, quantity_on_hand, lead_time_days, reorder_point AS existing_reorder
        FROM stock_levels
        WHERE store_id = ?
          AND snapshot_date = (SELECT MAX(snapshot_date) FROM stock_levels WHERE store_id = ?)
        """,
        [store_id, store_id],
    ).fetchdf()

    stock_map = {}
    if not stock_df.empty:
        stock_map = stock_df.set_index("product_id").to_dict("index")

    # Z-score for service level (e.g., 0.95 → 1.645)
    z_score = _z_for_service_level(service_level)

    # Compute per-product metrics
    products = []
    for pid, group in demand_df.groupby("product_id"):
        product_name = group["product_name"].iloc[0]
        category = group["category"].iloc[0]

        daily_units = group["daily_units"].astype(float)
        avg_daily_demand = float(daily_units.mean())
        std_daily_demand = float(daily_units.std()) if len(daily_units) > 1 else avg_daily_demand * 0.3
        total_units_sold = int(daily_units.sum())
        selling_days = len(daily_units)

        # Lead time
        stock_info = stock_map.get(str(pid), {})
        lead_time = int(stock_info.get("lead_time_days") or 7)
        current_stock = int(stock_info.get("quantity_on_hand") or 0)
        has_stock_data = str(pid) in stock_map

        # Safety stock = Z × σ_demand × √lead_time
        safety_stock = z_score * std_daily_demand * math.sqrt(lead_time)

        # Reorder point = (avg_demand × lead_time) + safety_stock
        reorder_point = (avg_daily_demand * lead_time) + safety_stock

        # Economic order quantity (simplified Wilson formula)
        # Assume ordering cost = 50, holding cost per unit per day = 0.1
        ordering_cost = 50
        holding_cost = 0.1
        if avg_daily_demand > 0:
            eoq = math.sqrt((2 * ordering_cost * avg_daily_demand * 365) / (holding_cost * 365))
        else:
            eoq = 0

        # Days of stock remaining
        days_of_stock = current_stock / avg_daily_demand if avg_daily_demand > 0 else 999

        # Status classification
        if not has_stock_data:
            status = "no_data"
        elif current_stock <= reorder_point * 0.5:
            status = "critical"
        elif current_stock <= reorder_point:
            status = "reorder_now"
        elif current_stock > avg_daily_demand * 90:
            status = "overstocked"
        else:
            status = "healthy"

        products.append({
            "product_id": str(pid),
            "product_name": product_name,
            "category": category,
            "avg_daily_demand": round(avg_daily_demand, 2),
            "std_daily_demand": round(std_daily_demand, 2),
            "total_units_sold": total_units_sold,
            "selling_days": selling_days,
            "lead_time_days": lead_time,
            "safety_stock": round(safety_stock, 0),
            "reorder_point": round(reorder_point, 0),
            "economic_order_qty": round(eoq, 0),
            "current_stock": current_stock,
            "days_of_stock": round(days_of_stock, 1),
            "has_stock_data": has_stock_data,
            "status": status,
        })

    # Sort: critical first, then reorder_now, then others
    status_order = {"critical": 0, "reorder_now": 1, "no_data": 2, "healthy": 3, "overstocked": 4}
    products.sort(key=lambda p: (status_order.get(p["status"], 5), -p["avg_daily_demand"]))

    needs_reorder = sum(1 for p in products if p["status"] in ("critical", "reorder_now"))
    overstocked = sum(1 for p in products if p["status"] == "overstocked")
    healthy = sum(1 for p in products if p["status"] == "healthy")
    no_data = sum(1 for p in products if p["status"] == "no_data")

    return {
        "products": products,
        "summary": {
            "total_products": len(products),
            "needs_reorder": needs_reorder,
            "overstocked": overstocked,
            "healthy": healthy,
            "no_stock_data": no_data,
        },
        "service_level": service_level,
        "period": period,
    }


def _z_for_service_level(sl: float) -> float:
    """Approximate Z-score for common service levels."""
    table = {
        0.90: 1.282,
        0.95: 1.645,
        0.97: 1.881,
        0.98: 2.054,
        0.99: 2.326,
    }
    closest = min(table, key=lambda k: abs(k - sl))
    return table[closest]
