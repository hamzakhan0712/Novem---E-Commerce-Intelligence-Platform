"""
Ad Spend ↔ Stock Level cross-correlation service.
Detects wasted ad spend (advertising out-of-stock products)
and computes category-level marketing ROI.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import duckdb

from app.core.database import get_duckdb_connection
from app.services.currency.currency_helper import sym as _sym

logger = logging.getLogger(__name__)

CATEGORY_KEYWORD_MAP: dict[str, list[str]] = {
    "Electronics": ["electronics", "gadget", "tech", "phone", "laptop", "computer", "tablet", "camera", "headphone", "speaker"],
    "Clothing": ["clothing", "fashion", "apparel", "shirt", "dress", "pant", "shoe", "wear", "jacket"],
    "Home": ["home", "furniture", "kitchen", "decor", "garden", "bed", "bath", "living"],
    "Books": ["book", "read", "novel", "guide", "manual", "journal"],
}


def _period_range(period: str) -> tuple[str, str]:
    """Return (start_date, end_date) strings for a period code."""
    now = datetime.now(timezone.utc)
    days_map = {"7d": 7, "14d": 14, "30d": 30, "90d": 90, "6m": 180, "12m": 365}
    days = days_map.get(period, 30)
    from datetime import timedelta
    start = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    end = now.strftime("%Y-%m-%d")
    return start, end


def _map_campaign_to_category(campaign_name: str) -> str:
    """Map a campaign name to a product category via keyword matching."""
    lower = campaign_name.lower()
    for category, keywords in CATEGORY_KEYWORD_MAP.items():
        for kw in keywords:
            if kw in lower:
                return category
    return "General"


def detect_wasted_spend(store_id: str, period: str = "30d") -> dict:
    """
    Detect campaigns spending on products that are out of stock.
    Joins ad_spend campaigns with stock_levels (qty=0) via category matching.
    """
    start_date, end_date = _period_range(period)
    conn = get_duckdb_connection()

    try:
        # Get campaigns with spend in the period
        campaigns = conn.execute(
            """
            SELECT
                campaign_name,
                channel,
                SUM(spend) as total_spend,
                SUM(impressions) as total_impressions,
                SUM(clicks) as total_clicks,
                SUM(conversions) as total_conversions,
                SUM(revenue_attributed) as total_revenue
            FROM ad_spend
            WHERE store_id = ?
              AND date BETWEEN ? AND ?
            GROUP BY campaign_name, channel
            ORDER BY total_spend DESC
            """,
            [store_id, start_date, end_date],
        ).fetchall()

        if not campaigns:
            return {
                "alerts": [],
                "total_wasted_spend": 0,
                "total_campaigns_flagged": 0,
                "message": "No ad spend data found for this period.",
            }

        # Get products currently out of stock (latest snapshot with qty=0)
        oos_products = conn.execute(
            """
            WITH latest AS (
                SELECT product_id, quantity_on_hand,
                       ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY snapshot_date DESC) as rn
                FROM stock_levels
                WHERE store_id = ?
            )
            SELECT l.product_id, p.product_name, p.category
            FROM latest l
            JOIN products p ON p.product_id = l.product_id AND p.store_id = ?
            WHERE l.rn = 1 AND l.quantity_on_hand = 0
            """,
            [store_id, store_id],
        ).fetchall()

        if not oos_products:
            return {
                "alerts": [],
                "total_wasted_spend": 0,
                "total_campaigns_flagged": 0,
                "message": "No products currently out of stock. No wasted spend detected.",
            }

        oos_categories = set()
        for _, _, cat in oos_products:
            if cat:
                oos_categories.add(cat.strip())

        alerts = []
        total_wasted = 0.0
        for campaign_name, channel, spend, impressions, clicks, conversions, revenue in campaigns:
            spend = float(spend)
            revenue = float(revenue)
            campaign_cat = _map_campaign_to_category(campaign_name)
            if campaign_cat in oos_categories:
                oos_in_cat = [name for _, name, cat in oos_products if cat and cat.strip() == campaign_cat]
                roas = round(revenue / spend, 2) if spend > 0 else 0
                alert = {
                    "campaign_name": campaign_name,
                    "channel": channel,
                    "category": campaign_cat,
                    "spend": round(spend, 2),
                    "revenue": round(revenue, 2),
                    "roas": roas,
                    "out_of_stock_products": oos_in_cat[:5],
                    "reason": f"Campaign targets {campaign_cat} category, but {len(oos_in_cat)} product(s) are out of stock",
                }
                alerts.append(alert)
                total_wasted += spend

        return {
            "alerts": alerts,
            "total_wasted_spend": round(total_wasted, 2),
            "total_campaigns_flagged": len(alerts),
            "message": f"{len(alerts)} campaign(s) may be wasting {_sym(store_id)}{total_wasted:,.0f} advertising out-of-stock products." if alerts else "No wasted spend detected.",
        }

    except duckdb.CatalogException:
        return {
            "alerts": [],
            "total_wasted_spend": 0,
            "total_campaigns_flagged": 0,
            "message": "Required tables not available for wasted spend analysis.",
        }
    except Exception as e:
        logger.error("detect_wasted_spend failed: %s", e)
        raise


def get_category_marketing_roi(store_id: str, period: str = "30d") -> dict:
    """
    Compare ad spend vs actual order revenue by product category.
    Ad spend is mapped to categories via campaign name keywords.
    Order revenue comes from the orders table.
    """
    start_date, end_date = _period_range(period)
    conn = get_duckdb_connection()

    try:
        # Get ad spend per campaign
        campaigns = conn.execute(
            """
            SELECT campaign_name, SUM(spend) as spend, SUM(revenue_attributed) as ad_revenue
            FROM ad_spend
            WHERE store_id = ? AND date BETWEEN ? AND ?
            GROUP BY campaign_name
            """,
            [store_id, start_date, end_date],
        ).fetchall()

        # Aggregate spend by category
        category_spend: dict[str, dict] = {}
        for campaign_name, spend, ad_revenue in campaigns:
            cat = _map_campaign_to_category(campaign_name)
            if cat not in category_spend:
                category_spend[cat] = {"spend": 0.0, "ad_revenue": 0.0}
            category_spend[cat]["spend"] += float(spend)
            category_spend[cat]["ad_revenue"] += float(ad_revenue)

        # Get actual order revenue by category
        order_revenue = conn.execute(
            """
            SELECT
                p.category,
                SUM(oi.quantity * oi.unit_price) as order_revenue,
                COUNT(DISTINCT o.order_id) as order_count
            FROM order_items oi
            JOIN orders o ON o.order_id = oi.order_id AND o.store_id = oi.store_id
            JOIN products p ON p.product_id = oi.product_id AND p.store_id = oi.store_id
            WHERE o.store_id = ? AND o.order_date BETWEEN ? AND ?
            GROUP BY p.category
            """,
            [store_id, start_date, end_date],
        ).fetchall()

        category_orders: dict[str, dict] = {}
        for cat, rev, count in order_revenue:
            display_cat = cat.strip() if cat else "Uncategorized"
            category_orders[display_cat] = {"order_revenue": round(float(rev), 2), "order_count": int(count)}

        # Merge results
        all_categories = set(list(category_spend.keys()) + list(category_orders.keys()))
        results = []
        for cat in sorted(all_categories):
            sp = category_spend.get(cat, {"spend": 0, "ad_revenue": 0})
            orders = category_orders.get(cat, {"order_revenue": 0, "order_count": 0})
            spend_val = round(sp["spend"], 2)
            order_rev = orders["order_revenue"]
            roas = round(order_rev / spend_val, 2) if spend_val > 0 else None
            results.append({
                "category": cat,
                "ad_spend": spend_val,
                "ad_attributed_revenue": round(sp["ad_revenue"], 2),
                "order_revenue": order_rev,
                "order_count": orders["order_count"],
                "roas": roas,
            })

        results.sort(key=lambda r: r["ad_spend"], reverse=True)

        return {"categories": results}

    except duckdb.CatalogException:
        return {"categories": [], "message": "Required tables not available for category ROI analysis."}
    except Exception as e:
        logger.error("get_category_marketing_roi failed: %s", e)
        raise
