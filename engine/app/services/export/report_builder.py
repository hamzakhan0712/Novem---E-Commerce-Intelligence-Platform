"""
Narrative BI Report Builder — Assembles intelligence data from all NOVEM
services and generates structured, human-readable report sections.

Two modes:
  - "technical": Detailed metrics, full breakdowns, percentages
  - "ceo":       Simple language, decisions-only, no jargon
"""

import logging
from datetime import datetime, timezone

from app.services.dashboard.kpi_calculator import calculate_kpis
from app.services.insights.insight_engine import (
    generate_insights,
    detect_anomalies,
    get_recommended_actions,
)
from app.services.insights.causal_engine import get_revenue_drivers
from app.services.insights.missed_revenue import detect_missed_revenue
from app.services.insights.health_score import calculate_health_score
from app.services.forecasting.forecast_service import (
    generate_forecast,
    get_forecast_metrics_overview,
)
from app.services.customers.customer_analytics import get_customer_summary
from app.services.products.product_analytics import get_product_summary
from app.services.sentiment.sentiment_service import get_sentiment_summary
from app.services.currency.currency_helper import sym as _sym

logger = logging.getLogger(__name__)


def build_report(store_id: str, period: str = "30d", mode: str = "technical") -> dict:
    """Collect data from all intelligence services and build a structured report.

    Returns a dict with named sections, each containing a title, narrative
    paragraphs, and supporting data for PDF rendering.
    """
    generated_at = datetime.now(timezone.utc).isoformat()

    # ── Gather data ──────────────────────────────────────────────
    kpis = _safe(lambda: calculate_kpis(store_id, period), {})
    health = _safe(lambda: calculate_health_score(store_id, period), {})
    drivers = _safe(lambda: get_revenue_drivers(store_id, period), {})
    insights = _safe(lambda: generate_insights(store_id, period), [])
    anomalies = _safe(lambda: detect_anomalies(store_id, period), [])
    actions = _safe(lambda: get_recommended_actions(store_id, period), [])
    missed = _safe(lambda: detect_missed_revenue(store_id, period), {})
    customers = _safe(lambda: get_customer_summary(store_id, period), {})
    products = _safe(lambda: get_product_summary(store_id, period), {})
    sentiment = _safe(lambda: get_sentiment_summary(store_id, period), {})
    forecast_overview = _safe(lambda: get_forecast_metrics_overview(store_id, 30), [])
    revenue_forecast = _safe(lambda: generate_forecast(store_id, "revenue", 30), {})

    is_ceo = mode == "ceo"

    # ── Build sections ───────────────────────────────────────────
    sections = {
        "meta": {
            "store_id": store_id,
            "period": period,
            "mode": mode,
            "generated_at": generated_at,
            "health_score": health.get("overall_score", 0),
            "health_label": health.get("label", "Unknown"),
        },
        "executive_summary": _build_executive_summary(kpis, health, drivers, forecast_overview, is_ceo),
        "kpi_overview": _build_kpi_section(kpis, is_ceo),
        "root_cause_analysis": _build_root_cause(drivers, is_ceo),
        "key_problems": _build_problems(anomalies, missed, insights, is_ceo),
        "recommendations": _build_recommendations(actions, is_ceo),
        "forecast": _build_forecast_section(forecast_overview, revenue_forecast, is_ceo),
        "customer_health": _build_customer_section(customers, is_ceo),
        "product_performance": _build_product_section(products, is_ceo),
        "sentiment_overview": _build_sentiment_section(sentiment, is_ceo),
        "health_components": _build_health_section(health, is_ceo),
    }

    return sections


# ── Section builders ─────────────────────────────────────────────


def _build_executive_summary(kpis: dict, health: dict, drivers: dict, forecasts: list, is_ceo: bool) -> dict:
    """The critical opening: a story, not numbers."""
    paragraphs: list[str] = []
    current = kpis.get("current", {})
    changes = kpis.get("changes", {})

    rev = current.get("revenue", 0)
    rev_change = changes.get("revenue", 0)
    orders = current.get("order_count", 0)
    order_change = changes.get("order_count", 0)
    cust_change = changes.get("unique_customers", 0)
    aov_change = changes.get("aov", 0)
    score = health.get("overall_score", 0)
    label = health.get("label", "Unknown")

    # Opening line — health verdict
    if is_ceo:
        if score >= 70:
            paragraphs.append(f"Your business is in good shape (Health Score: {score:.0f}/100 — {label}).")
        elif score >= 40:
            paragraphs.append(f"Your business needs attention (Health Score: {score:.0f}/100 — {label}).")
        else:
            paragraphs.append(f"Your business is at risk (Health Score: {score:.0f}/100 — {label}). Immediate action is needed.")
    else:
        paragraphs.append(f"Business Health Score: {score:.0f}/100 ({label}). "
                          f"Period revenue: {_sym(store_id)}{rev:,.0f}.")

    # Revenue story
    if rev_change > 0:
        driver_hint = _top_driver_hint(drivers, is_ceo)
        if is_ceo:
            paragraphs.append(f"Revenue grew {rev_change:.1f}%{driver_hint}.")
        else:
            paragraphs.append(f"Revenue increased {rev_change:.1f}% to {_sym(store_id)}{rev:,.0f} compared to the previous period{driver_hint}.")
    elif rev_change < 0:
        driver_hint = _top_driver_hint(drivers, is_ceo)
        if is_ceo:
            paragraphs.append(f"Revenue declined {abs(rev_change):.1f}%{driver_hint}.")
        else:
            paragraphs.append(f"Revenue decreased {abs(rev_change):.1f}% to {_sym(store_id)}{rev:,.0f}{driver_hint}.")
    else:
        paragraphs.append("Revenue was flat compared to the previous period.")

    # Key highlights
    highlights = []
    if order_change > 10:
        highlights.append(f"order volume up {order_change:.0f}%")
    elif order_change < -10:
        highlights.append(f"order volume down {abs(order_change):.0f}%")
    if cust_change > 10:
        highlights.append(f"customer base growing ({cust_change:+.0f}%)")
    elif cust_change < -10:
        highlights.append(f"customer acquisition declining ({cust_change:+.0f}%)")
    if aov_change > 10:
        highlights.append(f"customers spending more per order ({aov_change:+.0f}%)")
    elif aov_change < -10:
        highlights.append(f"average basket size shrinking ({aov_change:+.0f}%)")

    if highlights:
        if is_ceo:
            paragraphs.append("Key movements: " + "; ".join(highlights) + ".")
        else:
            paragraphs.append("Notable changes: " + "; ".join(highlights) + ".")

    # Forecast outlook
    rev_fc = next((f for f in forecasts if f["metric"] == "revenue"), None)
    if rev_fc and rev_fc.get("trend") not in ("unknown", "insufficient_data"):
        fc_change = rev_fc.get("change_pct", 0)
        if is_ceo:
            if fc_change > 2:
                paragraphs.append(f"Outlook: Revenue is expected to grow ~{fc_change:.0f}% over the next 30 days.")
            elif fc_change < -2:
                paragraphs.append(f"Warning: Revenue is projected to decline ~{abs(fc_change):.0f}% in the next 30 days.")
            else:
                paragraphs.append("Outlook: Revenue is expected to remain stable over the next 30 days.")
        else:
            paragraphs.append(f"30-day forecast: {rev_fc['trend']} trend ({fc_change:+.1f}%), "
                              f"projected total {_sym(store_id)}{rev_fc.get('forecast_total', 0):,.0f}.")

    return {"title": "Executive Summary", "paragraphs": paragraphs}


def _build_kpi_section(kpis: dict, is_ceo: bool) -> dict:
    """KPIs with explanations, not just values."""
    metrics: list[dict] = []
    current = kpis.get("current", {})
    changes = kpis.get("changes", {})

    for key, label, fmt in [
        ("revenue", "Revenue", "currency"),
        ("order_count", "Orders", "number"),
        ("unique_customers", "Unique Customers", "number"),
        ("aov", "Average Order Value", "currency"),
    ]:
        val = current.get(key, 0)
        chg = changes.get(key, 0)

        if fmt == "currency":
            val_str = f"{_sym(store_id)}{val:,.2f}"
        else:
            val_str = f"{val:,}"

        if is_ceo:
            if abs(chg) < 2:
                explanation = "Stable — no significant change."
            elif chg > 0:
                explanation = f"Up {chg:.1f}% — this is moving in the right direction."
            else:
                explanation = f"Down {abs(chg):.1f}% — this needs investigation."
        else:
            if abs(chg) < 2:
                explanation = f"Flat vs previous period ({chg:+.1f}%)."
            elif chg > 0:
                explanation = f"Increased {chg:.1f}% period-over-period."
            else:
                explanation = f"Decreased {abs(chg):.1f}% period-over-period."

        metrics.append({
            "label": label,
            "value": val_str,
            "change_pct": chg,
            "explanation": explanation,
        })

    return {"title": "KPI Overview", "metrics": metrics}


def _build_root_cause(drivers: dict, is_ceo: bool) -> dict:
    """Why revenue changed — decomposed into factors."""
    paragraphs: list[str] = []
    narrative = drivers.get("narrative", "")
    driver_list = drivers.get("drivers", [])

    change_pct = drivers.get("change_pct", 0)
    change_amt = drivers.get("change_amount", 0)

    if not driver_list:
        paragraphs.append("Insufficient data for root cause analysis.")
        return {"title": "Root Cause Analysis", "paragraphs": paragraphs, "drivers": []}

    if is_ceo:
        if change_amt > 0:
            paragraphs.append(f"Revenue grew {_sym(store_id)}{abs(change_amt):,.0f}. Here's why:")
        elif change_amt < 0:
            paragraphs.append(f"Revenue dropped {_sym(store_id)}{abs(change_amt):,.0f}. Here's what caused it:")
        else:
            paragraphs.append("Revenue was flat. Positive and negative factors balanced out:")

        for d in driver_list[:5]:
            direction = "added" if d["impact"] > 0 else "lost"
            paragraphs.append(f"• {d['driver']}: {direction} {_sym(store_id)}{abs(d['impact']):,.0f}")
    else:
        paragraphs.append(f"Revenue change: {change_pct:+.1f}% ({_sym(store_id)}{change_amt:+,.0f})")
        if narrative:
            paragraphs.append(narrative)

    return {"title": "Root Cause Analysis", "paragraphs": paragraphs, "drivers": driver_list[:5]}


def _build_problems(anomalies: list, missed: dict, insights: list, is_ceo: bool) -> dict:
    """Key problems ranked by severity/impact."""
    problems: list[dict] = []

    # From anomalies
    for a in anomalies[:5]:
        if is_ceo:
            problems.append({
                "severity": a.get("severity", "medium"),
                "title": f"Revenue {a['direction']} on {a['date']}",
                "description": f"{_sym(store_id)}{a['value']:,.0f} vs expected {_sym(store_id)}{a['expected']:,.0f}",
                "impact": abs(a["value"] - a["expected"]),
            })
        else:
            problems.append({
                "severity": a.get("severity", "medium"),
                "title": f"Revenue anomaly ({a['direction']}) on {a['date']}",
                "description": a["message"],
                "impact": abs(a["value"] - a["expected"]),
            })

    # From missed revenue
    total_missed = missed.get("total_missed_revenue", 0)
    breakdown = missed.get("breakdown", {})
    if total_missed > 0:
        parts = []
        for cat, data in breakdown.items():
            if data.get("total", 0) > 0:
                cat_label = cat.replace("_", " ").title()
                if is_ceo:
                    parts.append(f"{cat_label}: {_sym(store_id)}{data['total']:,.0f} lost")
                else:
                    parts.append(f"{cat_label}: {_sym(store_id)}{data['total']:,.0f} ({data.get('count', 0)} occurrences)")

        problems.append({
            "severity": "high" if total_missed > 1000 else "medium",
            "title": f"{_sym(store_id)}{total_missed:,.0f} in missed revenue opportunities",
            "description": "; ".join(parts) if parts else "Various revenue leaks detected.",
            "impact": total_missed,
        })

    # From negative insights
    for ins in insights:
        if ins.get("severity") in ("negative", "warning") and ins.get("priority", 50) <= 15:
            problems.append({
                "severity": "high" if ins["severity"] == "negative" else "medium",
                "title": ins["title"],
                "description": ins["message"] if not is_ceo else ins.get("suggestion", ins["message"]),
                "impact": 0,
            })

    problems.sort(key=lambda p: (0 if p["severity"] == "high" else 1, -p.get("impact", 0)))
    return {"title": "Key Problems", "problems": problems[:8]}


def _build_recommendations(actions: list, is_ceo: bool) -> dict:
    """Recommended actions with quantified impact."""
    items: list[dict] = []

    for a in actions[:6]:
        impact_usd = a.get("impact_dollars", 0)
        if is_ceo:
            items.append({
                "rank": a.get("rank", 0),
                "action": a["title"],
                "potential": f"{_sym(store_id)}{impact_usd:,.0f}" if impact_usd else "—",
                "effort": a.get("effort", "medium"),
                "description": a.get("description", ""),
            })
        else:
            items.append({
                "rank": a.get("rank", 0),
                "action": a["title"],
                "potential": f"{_sym(store_id)}{impact_usd:,.0f}" if impact_usd else "—",
                "effort": a.get("effort", "medium"),
                "confidence": f"{a.get('confidence', 0) * 100:.0f}%",
                "description": a.get("description", ""),
            })

    total_potential = sum(a.get("impact_dollars", 0) for a in actions[:6])
    summary = f"Total recoverable revenue: {_sym(store_id)}{total_potential:,.0f}" if total_potential > 0 else ""

    return {"title": "Recommended Actions", "actions": items, "summary": summary}


def _build_forecast_section(overview: list, revenue_fc: dict, is_ceo: bool) -> dict:
    """Forward-looking projections."""
    paragraphs: list[str] = []

    summary = revenue_fc.get("summary", {})
    method = revenue_fc.get("method", "unknown")

    if method in ("insufficient_data", "unknown"):
        paragraphs.append("Not enough historical data for reliable forecasting (need at least 14 days).")
        return {"title": "Forecast", "paragraphs": paragraphs, "metrics": []}

    fc_avg = summary.get("forecast_avg", 0)
    hist_avg = summary.get("historical_avg", 0)
    change = summary.get("change_pct", 0)
    peak_date = summary.get("peak_date", "")
    min_date = summary.get("min_date", "")
    total = summary.get("forecast_total", 0)

    if is_ceo:
        if change > 2:
            paragraphs.append(f"Revenue is expected to grow ~{change:.0f}% over the next 30 days (projected total: {_sym(store_id)}{total:,.0f}).")
        elif change < -2:
            paragraphs.append(f"Revenue is projected to decline ~{abs(change):.0f}% over the next 30 days.")
        else:
            paragraphs.append("Revenue is expected to stay roughly flat over the next 30 days.")

        if peak_date and min_date:
            paragraphs.append(f"Best expected day: {peak_date}. Weakest expected day: {min_date}.")
    else:
        paragraphs.append(f"30-day forecast using {method}: daily average {_sym(store_id)}{fc_avg:,.2f} "
                          f"(vs historical {_sym(store_id)}{hist_avg:,.2f}, {change:+.1f}%).")
        paragraphs.append(f"Projected 30-day total: {_sym(store_id)}{total:,.0f}.")
        if peak_date:
            paragraphs.append(f"Peak forecast date: {peak_date} ({_sym(store_id)}{summary.get('peak_value', 0):,.0f}). "
                              f"Trough: {min_date} ({_sym(store_id)}{summary.get('min_value', 0):,.0f}).")

    # All metrics summary
    metrics = []
    for m in overview:
        if m.get("trend") in ("unknown", "insufficient_data"):
            continue
        metrics.append({
            "metric": m["label"],
            "trend": m["trend"],
            "change_pct": m["change_pct"],
        })

    return {"title": "Forecast", "paragraphs": paragraphs, "metrics": metrics}


def _build_customer_section(data: dict, is_ceo: bool) -> dict:
    paragraphs: list[str] = []
    current = data.get("current", {})

    total = current.get("unique_customers", 0)
    returning_rate = current.get("returning_rate", 0)

    if not total:
        paragraphs.append("No customer data available for this period.")
        return {"title": "Customer Health", "paragraphs": paragraphs}

    if is_ceo:
        paragraphs.append(f"You had {total:,} unique customers this period.")
        if returning_rate >= 30:
            paragraphs.append(f"{returning_rate:.0f}% are repeat buyers — your customers are loyal.")
        elif returning_rate >= 15:
            paragraphs.append(f"{returning_rate:.0f}% are returning customers — average loyalty.")
        else:
            paragraphs.append(f"Only {returning_rate:.0f}% came back. Customer loyalty needs work.")
    else:
        paragraphs.append(f"Unique customers: {total:,}. Returning rate: {returning_rate:.1f}%.")
        avg_ltv = current.get("avg_lifetime_value", 0)
        if avg_ltv:
            paragraphs.append(f"Average customer lifetime value: {_sym(store_id)}{avg_ltv:,.2f}.")

    return {"title": "Customer Health", "paragraphs": paragraphs}


def _build_product_section(data: dict, is_ceo: bool) -> dict:
    paragraphs: list[str] = []
    current = data.get("current", {})

    total_products = current.get("total_products", 0)
    total_revenue = current.get("total_revenue", 0)
    categories = current.get("total_categories", 0)

    if not total_products:
        paragraphs.append("No product data available for this period.")
        return {"title": "Product Performance", "paragraphs": paragraphs}

    if is_ceo:
        paragraphs.append(f"{total_products:,} products sold across {categories} categories, "
                          f"generating {_sym(store_id)}{total_revenue:,.0f} in revenue.")
    else:
        paragraphs.append(f"Products sold: {total_products:,}. Categories: {categories}. "
                          f"Total revenue: {_sym(store_id)}{total_revenue:,.0f}.")

    return {"title": "Product Performance", "paragraphs": paragraphs}


def _build_sentiment_section(data: dict, is_ceo: bool) -> dict:
    paragraphs: list[str] = []
    current = data.get("current", {})

    total_reviews = current.get("total_reviews", 0)
    avg_rating = current.get("avg_rating", 0)
    positive_ratio = current.get("positive_ratio", 0)

    if not total_reviews:
        paragraphs.append("No review data available for this period.")
        return {"title": "Customer Sentiment", "paragraphs": paragraphs}

    if is_ceo:
        if avg_rating >= 4.0:
            paragraphs.append(f"Customers are happy — average rating {avg_rating:.1f}/5 across {total_reviews:,} reviews.")
        elif avg_rating >= 3.0:
            paragraphs.append(f"Customer satisfaction is average — {avg_rating:.1f}/5 across {total_reviews:,} reviews. Room for improvement.")
        else:
            paragraphs.append(f"Customer satisfaction is low — {avg_rating:.1f}/5 across {total_reviews:,} reviews. This needs urgent attention.")
    else:
        paragraphs.append(f"Reviews: {total_reviews:,}. Average rating: {avg_rating:.1f}/5. "
                          f"Positive sentiment: {positive_ratio:.0f}%.")

    return {"title": "Customer Sentiment", "paragraphs": paragraphs}


def _build_health_section(health: dict, is_ceo: bool) -> dict:
    components = health.get("components", {})
    if not components:
        return {"title": "Business Health Breakdown", "components": []}

    items: list[dict] = []
    for key, comp in components.items():
        label = key.replace("_", " ").title()
        score = comp.get("score", 0)
        weight = comp.get("weight", 0)
        detail = comp.get("detail", "")

        if is_ceo:
            if score >= 70:
                status = "Good"
            elif score >= 40:
                status = "Needs Attention"
            else:
                status = "Critical"
            items.append({"label": label, "score": score, "status": status})
        else:
            items.append({"label": label, "score": score, "weight": f"{weight * 100:.0f}%", "detail": detail})

    return {"title": "Business Health Breakdown", "components": items}


# ── Helpers ──────────────────────────────────────────────────────


def _safe(fn, default):
    """Call fn, return default on any exception."""
    try:
        return fn()
    except Exception as exc:
        logger.warning("Report data collection failed: %s", exc)
        return default


def _top_driver_hint(drivers: dict, is_ceo: bool) -> str:
    """Extract a hint about the top revenue driver."""
    top_drivers = drivers.get("drivers", [])
    if not top_drivers:
        return ""
    top = top_drivers[0]
    if is_ceo:
        if top["impact"] > 0:
            return f", mainly driven by {top['driver'].lower()}"
        return f", primarily due to {top['driver'].lower()} decline"
    return f" (primary driver: {top['driver']}, {_sym(store_id)}{top['impact']:+,.0f})"
