"""
Explain This Metric — generates plain-language explanations for any KPI,
using the causal engine and contextual factors.
"""

import logging

from app.services.dashboard.kpi_calculator import calculate_kpis
from app.services.insights.causal_engine import get_metric_breakdown
from app.services.currency.currency_helper import sym as _sym

logger = logging.getLogger(__name__)

METRIC_DESCRIPTIONS = {
    "revenue": "Total revenue from completed orders in this period",
    "order_count": "Total number of orders placed",
    "unique_customers": "Number of distinct customers who placed orders",
    "aov": "Average Order Value — total revenue divided by number of orders",
}


def explain_metric(store_id: str, metric: str, period: str = "30d") -> dict:
    """Generate a comprehensive explanation of a metric's current state."""
    kpis = calculate_kpis(store_id, period)
    current = kpis.get("current", {})
    previous = kpis.get("previous", {})
    changes = kpis.get("changes", {})

    metric_key = _normalize_metric(metric)
    cur_val = current.get(metric_key, 0) or 0
    prev_val = previous.get(metric_key, 0) or 0

    change_key = metric_key if metric_key != "unique_customers" else "unique_customers"
    pct_key = f"{change_key}" if change_key in changes else change_key
    change_pct = changes.get(pct_key, 0) or 0

    # Get drivers if revenue
    drivers = []
    narrative = ""
    if metric_key == "revenue":
        try:
            breakdown = get_metric_breakdown(store_id, "revenue", period)
            drivers = breakdown.get("drivers", [])
            narrative = breakdown.get("narrative", "")
        except Exception:
            pass

    # Build explanation
    description = METRIC_DESCRIPTIONS.get(metric_key, f"The {metric_key} metric for your store")
    explanation_parts = [description + "."]

    if cur_val > 0:
        if metric_key in ("revenue", "aov"):
            explanation_parts.append(f"Currently at {_sym(store_id)}{cur_val:,.2f}, compared to {_sym(store_id)}{prev_val:,.2f} in the previous period.")
        else:
            explanation_parts.append(f"Currently at {cur_val:,.0f}, compared to {prev_val:,.0f} in the previous period.")

    if abs(change_pct) > 1:
        direction = "increased" if change_pct > 0 else "decreased"
        explanation_parts.append(f"This {direction} by {abs(change_pct):.1f}% period-over-period.")

    if narrative:
        explanation_parts.append(narrative)

    # Add contextual guidance
    guidance = _get_guidance(metric_key, change_pct, cur_val)
    if guidance:
        explanation_parts.append(guidance)

    return {
        "metric": metric_key,
        "current_value": cur_val,
        "previous_value": prev_val,
        "change_pct": change_pct,
        "description": description,
        "explanation": " ".join(explanation_parts),
        "drivers": drivers[:5],
        "guidance": guidance,
        "period": period,
    }


def _normalize_metric(metric: str) -> str:
    aliases = {
        "revenue": "revenue",
        "orders": "order_count",
        "order_count": "order_count",
        "customers": "unique_customers",
        "unique_customers": "unique_customers",
        "aov": "aov",
        "average_order_value": "aov",
    }
    return aliases.get(metric.lower(), metric.lower())


def _get_guidance(metric: str, change_pct: float, value: float) -> str:
    if metric == "revenue":
        if change_pct < -15:
            return "This is a significant decline. Check the Revenue Drivers breakdown to understand the root causes."
        if change_pct < -5:
            return "Revenue is trending down. Review which categories or channels lost momentum and check for increased refunds."
        if change_pct < 0:
            return "A slight dip — monitor over the next period. Check if a seasonal pattern or a one-off event is responsible."
        if change_pct > 20:
            return "Strong growth! Consider scaling your best-performing channels and products."
        if change_pct > 5:
            return "Healthy growth. Identify which channels and products are driving the increase to double down."
        if change_pct > 0:
            return "Marginal growth — look for opportunities to accelerate via promotions or new channels."
    elif metric == "order_count":
        if change_pct < -20:
            return "Order volume is dropping sharply. Review marketing campaigns, site traffic, and conversion rates."
        if change_pct < -5:
            return "Orders are declining. Check if acquisition channels slowed down or if returning customers are ordering less frequently."
        if change_pct < 0:
            return "Slight drop in orders — could be seasonal. Monitor closely."
        if change_pct > 15:
            return "Strong order growth! Ensure fulfillment capacity can handle the increase."
        if change_pct > 0:
            return "Orders ticking up — a positive sign. Look at which channels are contributing most."
    elif metric == "aov":
        if change_pct < -10:
            return "Customers are spending less per order. Try bundling or cross-sell strategies to lift basket size."
        if change_pct < 0:
            return "Average order value dipped slightly. Check if heavier discounting or a shift to lower-price products is the cause."
        if change_pct > 15:
            return "Basket sizes are growing — identify which products drive the higher values and promote them further."
        if change_pct > 0:
            return "AOV is improving. Upsell and cross-sell strategies may be working."
    elif metric == "unique_customers":
        if change_pct < -15:
            return "Customer acquisition is slowing significantly. Evaluate your ad spend, landing pages, and acquisition channels."
        if change_pct < -5:
            return "Fewer new customers this period. Review whether marketing budgets were reduced or if competitors are capturing traffic."
        if change_pct < 0:
            return "Slight decline in unique customers. Keep an eye on acquisition funnels."
        if change_pct > 15:
            return "Customer acquisition is surging. Make sure the new cohort retains with a strong post-purchase experience."
        if change_pct > 0:
            return "Steady customer growth — a healthy sign for long-term revenue."
    return ""
