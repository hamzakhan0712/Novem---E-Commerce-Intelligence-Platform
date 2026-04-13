"""
Insight engine — generates plain-language insights from store data,
detects anomalies, and recommends actions.
"""

import logging
from datetime import datetime, timedelta, timezone

from app.core.database import get_duckdb_connection, get_sqlite_connection
from app.services.dashboard.kpi_calculator import calculate_kpis
from app.services.currency.currency_helper import sym as _sym

logger = logging.getLogger(__name__)


_PERIOD_DAYS = {
    "7d": 7, "14d": 14, "30d": 30, "60d": 60, "90d": 90,
    "6m": 182, "12m": 365,
}


def _period_start(period: str) -> str:
    """Return ISO date string for the start of the given period."""
    days = _PERIOD_DAYS.get(period, 30)
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")


def generate_insights(store_id: str, period: str = "30d") -> list[dict]:
    """Generate a ranked list of plain-language insights for a store."""
    insights: list[dict] = []

    kpi_insights = _kpi_insights(store_id, period)
    insights.extend(kpi_insights)

    customer_insights = _customer_insights(store_id, period)
    insights.extend(customer_insights)

    product_insights = _product_insights(store_id, period)
    insights.extend(product_insights)

    insights.sort(key=lambda x: x.get("priority", 50))

    # Add confidence scores based on data completeness
    for ins in insights:
        sev = ins.get("severity", "info")
        pri = ins.get("priority", 50)
        base = 0.65 if sev in ("negative", "positive") else 0.55
        boost = max(0, (50 - pri)) * 0.005
        ins["confidence"] = round(min(0.95, base + boost), 2)

    return insights


def _kpi_insights(store_id: str, period: str) -> list[dict]:
    insights: list[dict] = []
    kpis = calculate_kpis(store_id, period)
    changes = kpis.get("changes", {})
    current = kpis.get("current", {})

    revenue_change = changes.get("revenue")
    if revenue_change is not None:
        if revenue_change > 15:
            insights.append({
                "type": "kpi",
                "category": "revenue",
                "severity": "positive",
                "priority": 10,
                "title": "Revenue is growing strongly",
                "message": f"Revenue increased {revenue_change:.1f}% compared to the previous period, reaching {_sym(store_id)}{current.get('revenue', 0):,.0f}.",
                "suggestion": "Consider scaling marketing spend to capitalize on this momentum.",
            })
        elif revenue_change < -15:
            insights.append({
                "type": "kpi",
                "category": "revenue",
                "severity": "negative",
                "priority": 5,
                "title": "Revenue decline detected",
                "message": f"Revenue dropped {abs(revenue_change):.1f}% compared to the previous period.",
                "suggestion": "Review recent marketing campaigns, product availability, and pricing changes.",
            })

    order_change = changes.get("order_count")
    if order_change is not None and order_change < -20:
        insights.append({
            "type": "kpi",
            "category": "orders",
            "severity": "negative",
            "priority": 8,
            "title": "Order volume declining",
            "message": f"Orders dropped {abs(order_change):.1f}% this period. This may indicate reduced customer engagement.",
            "suggestion": "Consider running promotional campaigns or reviewing your product catalog.",
        })

    aov_change = changes.get("aov")
    if aov_change is not None:
        if aov_change > 20:
            insights.append({
                "type": "kpi",
                "category": "aov",
                "severity": "info",
                "priority": 20,
                "title": "Average order value increased significantly",
                "message": f"AOV rose {aov_change:.1f}% to {_sym(store_id)}{current.get('aov', 0):,.2f}. Customers are spending more per order.",
                "suggestion": "Investigate which products are driving higher basket sizes and feature them prominently.",
            })
        elif aov_change < -15:
            insights.append({
                "type": "kpi",
                "category": "aov",
                "severity": "warning",
                "priority": 15,
                "title": "Average order value dropping",
                "message": f"AOV decreased {abs(aov_change):.1f}%. Customers may be shifting to cheaper items.",
                "suggestion": "Try cross-selling or bundling strategies to increase basket size.",
            })

    customer_change = changes.get("unique_customers")
    if customer_change is not None:
        if customer_change > 25:
            insights.append({
                "type": "kpi",
                "category": "customers",
                "severity": "positive",
                "priority": 12,
                "title": "Customer acquisition surging",
                "message": f"Unique customers increased {customer_change:.1f}% compared to the previous period.",
                "suggestion": "Identify which channels are driving new customers and double down on them.",
            })
        elif customer_change < -20:
            insights.append({
                "type": "kpi",
                "category": "customers",
                "severity": "negative",
                "priority": 7,
                "title": "Customer acquisition slowing",
                "message": f"Unique customers dropped {abs(customer_change):.1f}% this period.",
                "suggestion": "Review your acquisition channels and consider new customer incentives.",
            })

    return insights


def _customer_insights(store_id: str, period: str) -> list[dict]:
    insights: list[dict] = []
    conn = get_duckdb_connection()
    start_date = _period_start(period)

    row = conn.execute(
        """SELECT
             COUNT(DISTINCT customer_id) as total,
             COUNT(DISTINCT CASE WHEN order_count > 1 THEN customer_id END) as returning
           FROM (
             SELECT customer_id, COUNT(DISTINCT order_id) as order_count
             FROM orders WHERE store_id = ? AND order_date >= ? AND status = 'completed'
             GROUP BY customer_id
           )""",
        [store_id, start_date],
    ).fetchone()

    if row and row[0] > 0:
        total, returning = row[0], row[1]
        repeat_rate = (returning / total) * 100

        if repeat_rate < 15:
            insights.append({
                "type": "customer",
                "category": "retention",
                "severity": "warning",
                "priority": 12,
                "title": "Low customer retention",
                "message": f"Only {repeat_rate:.0f}% of customers placed more than one order this period ({returning:,} of {total:,}).",
                "suggestion": "Implement a loyalty program or post-purchase email sequence to encourage repeat purchases.",
            })
        elif repeat_rate > 40:
            insights.append({
                "type": "customer",
                "category": "retention",
                "severity": "positive",
                "priority": 25,
                "title": "Strong customer loyalty",
                "message": f"{repeat_rate:.0f}% of customers are repeat buyers this period ({returning:,} of {total:,}).",
                "suggestion": "Leverage your loyal base with referral programs to drive new customer acquisition.",
            })

    # Top customer concentration
    top_row = conn.execute(
        """WITH ranked AS (
             SELECT customer_id, SUM(total_price - discount_amount) as spend,
                    ROW_NUMBER() OVER (ORDER BY SUM(total_price - discount_amount) DESC) as rn,
                    COUNT(*) OVER () as total_customers
             FROM orders WHERE store_id = ? AND order_date >= ? AND status = 'completed'
             GROUP BY customer_id
           )
           SELECT
             SUM(CASE WHEN rn <= GREATEST(CEIL(total_customers * 0.1), 1) THEN spend ELSE 0 END) * 100.0
               / NULLIF(SUM(spend), 0)
           FROM ranked""",
        [store_id, start_date],
    ).fetchone()

    if top_row and top_row[0] is not None and top_row[0] > 50:
        insights.append({
            "type": "customer",
            "category": "concentration",
            "severity": "warning",
            "priority": 18,
            "title": "Revenue concentrated in few customers",
            "message": f"Top 10% of customers account for {top_row[0]:.0f}% of revenue this period.",
            "suggestion": "Diversify your customer base to reduce dependency on a few high-value customers.",
        })

    return insights


def _product_insights(store_id: str, period: str) -> list[dict]:
    insights: list[dict] = []
    conn = get_duckdb_connection()
    start_date = _period_start(period)

    # Category diversity
    cat_row = conn.execute(
        "SELECT COUNT(DISTINCT category) FROM orders WHERE store_id = ? AND order_date >= ? AND category IS NOT NULL AND status = 'completed'",
        [store_id, start_date],
    ).fetchone()

    if cat_row and cat_row[0] is not None:
        cat_count = cat_row[0]
        if cat_count == 1:
            insights.append({
                "type": "product",
                "category": "diversity",
                "severity": "info",
                "priority": 30,
                "title": "Single product category",
                "message": "All orders in this period are in a single product category.",
                "suggestion": "Consider expanding your product range to attract different customer segments.",
            })

    # Top product concentration
    prod_row = conn.execute(
        """WITH ranked AS (
             SELECT product_name, SUM(total_price - discount_amount) as rev,
                    ROW_NUMBER() OVER (ORDER BY SUM(total_price - discount_amount) DESC) as rn
             FROM orders WHERE store_id = ? AND order_date >= ? AND product_name IS NOT NULL AND status = 'completed'
             GROUP BY product_name
           )
           SELECT
             SUM(CASE WHEN rn <= 3 THEN rev ELSE 0 END) * 100.0 / NULLIF(SUM(rev), 0),
             COUNT(*)
           FROM ranked""",
        [store_id, start_date],
    ).fetchone()

    if prod_row and prod_row[0] is not None and prod_row[1] > 5 and prod_row[0] > 60:
        insights.append({
            "type": "product",
            "category": "concentration",
            "severity": "warning",
            "priority": 16,
            "title": "Revenue depends on few products",
            "message": f"Top 3 products generate {prod_row[0]:.0f}% of revenue across {prod_row[1]} products.",
            "suggestion": "Promote underperforming products or expand your catalog to reduce risk.",
        })

    # Refund rate
    refund_row = conn.execute(
        """SELECT
             COUNT(DISTINCT CASE WHEN status = 'refunded' THEN order_id END) as refunds,
             COUNT(DISTINCT CASE WHEN status IN ('completed', 'refunded') THEN order_id END) as total
           FROM orders WHERE store_id = ? AND order_date >= ?""",
        [store_id, start_date],
    ).fetchone()

    if refund_row and refund_row[1] > 0:
        refund_rate = (refund_row[0] / refund_row[1]) * 100
        if refund_rate > 10:
            insights.append({
                "type": "product",
                "category": "refunds",
                "severity": "warning",
                "priority": 10,
                "title": "High refund rate",
                "message": f"{refund_rate:.1f}% of orders have been refunded this period. This is above the typical 5-8% range.",
                "suggestion": "Review product descriptions, sizing guides, and quality control processes.",
            })

    return insights


def detect_anomalies(store_id: str, period: str = "30d") -> list[dict]:
    """Detect statistical anomalies in daily revenue."""
    anomalies: list[dict] = []
    conn = get_duckdb_connection()
    start_date = _period_start(period)

    rows = conn.execute(
        """SELECT order_date::DATE as d, SUM(total_price - discount_amount) as daily_rev
           FROM orders WHERE store_id = ? AND order_date >= ? AND status = 'completed'
           GROUP BY d ORDER BY d""",
        [store_id, start_date],
    ).fetchall()

    if len(rows) < 14:
        return anomalies

    revenues = [float(r[1]) for r in rows]
    window = 7
    for i in range(window, len(revenues)):
        window_vals = revenues[i - window:i]
        mean = sum(window_vals) / len(window_vals)
        if mean == 0:
            continue
        std = (sum((v - mean) ** 2 for v in window_vals) / len(window_vals)) ** 0.5
        if std == 0:
            continue

        z_score = (revenues[i] - mean) / std
        date_str = str(rows[i][0])

        if abs(z_score) > 2.5:
            direction = "spike" if z_score > 0 else "drop"
            severity = "high" if abs(z_score) > 3.5 else "medium" if abs(z_score) > 3.0 else "low"
            confidence = min(0.99, 0.5 + (abs(z_score) - 2.5) * 0.15 + min(i, 30) * 0.005)
            detected_at = datetime.now(timezone.utc).isoformat()
            # Time-to-detection: hours between anomaly day end and now
            try:
                anomaly_date = datetime.strptime(date_str, "%Y-%m-%d").replace(
                    hour=23, minute=59, tzinfo=timezone.utc
                )
                detection_hours = round(
                    (datetime.now(timezone.utc) - anomaly_date).total_seconds() / 3600, 1
                )
            except Exception:
                detection_hours = None
            anomalies.append({
                "date": date_str,
                "metric": "revenue",
                "value": round(revenues[i], 2),
                "expected": round(mean, 2),
                "z_score": round(abs(z_score), 2),
                "direction": direction,
                "severity": severity,
                "confidence": round(confidence, 2),
                "detected_at": detected_at,
                "time_to_detection_hours": detection_hours,
                "message": f"Daily revenue was {abs(z_score):.1f}σ {'above' if direction == 'spike' else 'below'} the 7-day average ({_sym(store_id)}{revenues[i]:,.0f} vs {_sym(store_id)}{mean:,.0f}).",
            })

    anomalies.sort(key=lambda x: x["z_score"], reverse=True)
    return anomalies[:10]


def get_recommended_actions(store_id: str, period: str = "30d") -> list[dict]:
    """Generate data-driven action recommendations quantified with dollar impacts."""
    actions: list[dict] = []
    kpis = calculate_kpis(store_id, period)
    changes = kpis.get("changes", {})
    current = kpis.get("current", {})
    conn = get_duckdb_connection()
    start_date = _period_start(period)

    revenue = current.get("revenue", 0) or 0
    aov = current.get("aov", 0) or 0
    order_count = current.get("order_count", 0) or 0
    revenue_change = changes.get("revenue", 0) or 0

    # 1) Refund reduction opportunity
    refund_row = conn.execute(
        """SELECT
             COALESCE(SUM(CASE WHEN status = 'refunded' THEN total_price - discount_amount END), 0) as refund_total,
             COUNT(DISTINCT CASE WHEN status = 'refunded' THEN order_id END) as refund_orders,
             COUNT(DISTINCT CASE WHEN status IN ('completed', 'refunded') THEN order_id END) as total_orders
           FROM orders WHERE store_id = ? AND order_date >= ?""",
        [store_id, start_date],
    ).fetchone()
    if refund_row:
        ref_total = float(refund_row[0])
        ref_orders = int(refund_row[1])
        total_orders = int(refund_row[2])
        ref_rate = (ref_orders / total_orders * 100) if total_orders > 0 else 0
        if ref_rate > 5 and ref_total > 0:
            # Target: reduce refund rate to 5%
            target_refunds = total_orders * 0.05
            saveable = max(0, ref_orders - target_refunds)
            impact_dollars = round((saveable / max(ref_orders, 1)) * ref_total, 0)
            actions.append({
                "rank": 0,
                "priority": "high",
                "category": "refunds",
                "title": "Reduce refund rate to recover revenue",
                "description": f"Refund rate is {ref_rate:.1f}% ({ref_orders} orders, {_sym(store_id)}{ref_total:,.0f}). Improving product descriptions, QA, and sizing can reduce this to ~5%.",
                "impact": "high",
                "effort": "medium",
                "impact_dollars": impact_dollars,
                "confidence": 0.7,
            })

    # 2) At-risk customer recovery
    atrisk_row = conn.execute(
        """WITH customer_activity AS (
             SELECT customer_id,
                    MAX(order_date) as last_order,
                    COUNT(DISTINCT order_id) as orders,
                    SUM(total_price - discount_amount) as lifetime_spend
             FROM orders WHERE store_id = ? AND status = 'completed' GROUP BY customer_id
           )
           SELECT COUNT(*) as cnt, COALESCE(AVG(lifetime_spend), 0) as avg_spend
           FROM customer_activity
           WHERE orders >= 2
             AND last_order < ?
             AND last_order >= CAST(? AS DATE) - INTERVAL '90' DAY""",
        [store_id, start_date, start_date],
    ).fetchone()
    if atrisk_row and int(atrisk_row[0]) > 0:
        at_risk_count = int(atrisk_row[0])
        avg_spend = float(atrisk_row[1])
        # Assume 20% win-back rate with targeted campaign
        impact_dollars = round(at_risk_count * avg_spend * 0.20, 0)
        actions.append({
            "rank": 0,
            "priority": "high",
            "category": "retention",
            "title": f"Re-engage {at_risk_count} at-risk repeat customers",
            "description": f"{at_risk_count} customers with 2+ orders haven't purchased in 90+ days (avg lifetime spend {_sym(store_id)}{avg_spend:,.0f}). A targeted win-back campaign could recover ~20%.",
            "impact": "high",
            "effort": "medium",
            "impact_dollars": impact_dollars,
            "confidence": 0.6,
        })

    # 3) AOV opportunity — cross-sell / bundle
    if aov > 0 and order_count > 20:
        target_aov_increase = aov * 0.10  # 10% uplift
        impact_dollars = round(order_count * target_aov_increase, 0)
        actions.append({
            "rank": 0,
            "priority": "medium",
            "category": "aov",
            "title": "Increase average order value with bundles",
            "description": f"Current AOV is {_sym(store_id)}{aov:,.2f}. Adding product bundles and 'frequently bought together' recommendations can lift AOV by 10%.",
            "impact": "medium",
            "effort": "low",
            "impact_dollars": impact_dollars,
            "confidence": 0.5,
        })

    # 4) Launch promotional campaign if revenue declining
    if revenue_change < -10 and revenue > 0:
        gap = abs(revenue_change) / 100 * revenue
        impact_dollars = round(gap * 0.5, 0)  # Recover 50% of the gap
        actions.append({
            "rank": 0,
            "priority": "high",
            "category": "revenue",
            "title": "Launch targeted promotional campaign",
            "description": f"Revenue dropped {abs(revenue_change):.0f}% (−{_sym(store_id)}{gap:,.0f}). A focused promotion could recover ~50% of the decline.",
            "impact": "high",
            "effort": "medium",
            "impact_dollars": impact_dollars,
            "confidence": 0.5,
        })

    # 5) Channel expansion
    channel_row = conn.execute(
        """SELECT COUNT(DISTINCT channel) FROM orders
           WHERE store_id = ? AND order_date >= ? AND channel IS NOT NULL AND status = 'completed'""",
        [store_id, start_date],
    ).fetchone()
    channel_count = channel_row[0] if channel_row else 0
    if channel_count <= 2 and revenue > 0:
        impact_dollars = round(revenue * 0.25, 0)  # 25% uplift from new channels
        actions.append({
            "rank": 0,
            "priority": "medium",
            "category": "channels",
            "title": "Expand to additional sales channels",
            "description": f"Only {channel_count} active channel(s). Adding marketplaces like Amazon or social commerce can increase reach by 20-40%.",
            "impact": "high",
            "effort": "high",
            "impact_dollars": impact_dollars,
            "confidence": 0.4,
        })

    # 6) Improve retention
    ret_row = conn.execute(
        """SELECT
             COUNT(DISTINCT CASE WHEN oc > 1 THEN cid END) * 100.0 / NULLIF(COUNT(DISTINCT cid), 0)
           FROM (
             SELECT customer_id as cid, COUNT(DISTINCT order_id) as oc
             FROM orders WHERE store_id = ? AND order_date >= ? AND status = 'completed'
             GROUP BY customer_id
           )""",
        [store_id, start_date],
    ).fetchone()
    repeat_rate = ret_row[0] if ret_row and ret_row[0] is not None else 0
    if repeat_rate < 20 and order_count > 0:
        # Each retained customer worth ~1.5x first purchase
        new_retained = round(order_count * 0.10)
        impact_dollars = round(new_retained * aov * 1.5, 0)
        actions.append({
            "rank": 0,
            "priority": "high",
            "category": "retention",
            "title": "Set up post-purchase email automation",
            "description": f"Repeat rate is only {repeat_rate:.0f}%. Automated follow-ups could convert ~10% of one-time buyers into repeat customers.",
            "impact": "high",
            "effort": "medium",
            "impact_dollars": impact_dollars,
            "confidence": 0.55,
        })

    # Sort by impact_dollars descending and assign ranks
    actions.sort(key=lambda x: x.get("impact_dollars", 0), reverse=True)
    for i, a in enumerate(actions, 1):
        a["rank"] = i

    return actions


def get_insight_summary(store_id: str, period: str = "30d") -> dict:
    """Return summary counts of insights, anomalies, and actions."""
    insights = generate_insights(store_id, period)
    anomalies = detect_anomalies(store_id, period)
    actions = get_recommended_actions(store_id, period)

    critical = sum(1 for i in insights if i.get("priority", 50) <= 10)
    warning = sum(1 for i in insights if 10 < i.get("priority", 50) <= 20)
    info = sum(1 for i in insights if i.get("priority", 50) > 20)
    categories = sorted(set(i["category"] for i in insights))

    return {
        "total_insights": len(insights),
        "critical_count": critical,
        "warning_count": warning,
        "info_count": info,
        "anomaly_count": len(anomalies),
        "action_count": len(actions),
        "categories": categories,
    }
