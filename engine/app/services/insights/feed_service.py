"""
Auto Insight Feed — aggregates insights, anomalies, actions, drivers,
and missed revenue into a single prioritized timeline.
"""

import logging
from datetime import datetime, timezone

from app.services.insights.insight_engine import (
    detect_anomalies,
    generate_insights,
    get_recommended_actions,
)
from app.services.insights.causal_engine import get_revenue_drivers
from app.services.insights.missed_revenue import detect_missed_revenue
from app.services.currency.currency_helper import sym as _sym

logger = logging.getLogger(__name__)


def build_insight_feed(store_id: str, period: str = "30d") -> list[dict]:
    """Build a unified, priority-sorted feed of all intelligence items."""
    feed: list[dict] = []
    now = datetime.now(timezone.utc).isoformat()

    # Gather all data sources (tolerate individual failures)
    try:
        insights = generate_insights(store_id, period)
    except Exception:
        insights = []

    try:
        anomalies = detect_anomalies(store_id, period)
    except Exception:
        anomalies = []

    try:
        actions = get_recommended_actions(store_id, period)
    except Exception:
        actions = []

    try:
        drivers = get_revenue_drivers(store_id, period)
    except Exception:
        drivers = {"drivers": []}

    try:
        missed = detect_missed_revenue(store_id, period)
    except Exception:
        missed = {"total_missed_revenue": 0, "opportunities": []}

    # Convert insights to feed items
    for i, ins in enumerate(insights):
        feed.append({
            "id": f"insight-{i}",
            "feed_type": "insight",
            "severity": ins.get("severity", "info"),
            "priority": ins.get("priority", 50),
            "title": ins["title"],
            "message": ins["message"],
            "suggestion": ins.get("suggestion"),
            "category": ins.get("category", "general"),
            "timestamp": now,
        })

    # Convert anomalies
    for i, a in enumerate(anomalies):
        sev_map = {"high": "negative", "medium": "warning", "low": "info"}
        pri_map = {"high": 3, "medium": 12, "low": 25}
        feed.append({
            "id": f"anomaly-{i}",
            "feed_type": "anomaly",
            "severity": sev_map.get(a["severity"], "info"),
            "priority": pri_map.get(a["severity"], 20),
            "title": f"Revenue {a['direction']} detected",
            "message": a["message"],
            "category": "anomaly",
            "timestamp": a.get("date", now),
            "metadata": {
                "value": a["value"],
                "expected": a["expected"],
                "z_score": a["z_score"],
            },
        })

    # Convert actions
    for a in actions:
        impact = a.get("impact_dollars", 0)
        pri = 6 if a.get("priority") == "high" else 15
        feed.append({
            "id": f"action-{a['rank']}",
            "feed_type": "action",
            "severity": "positive" if impact > 0 else "info",
            "priority": pri,
            "title": a["title"],
            "message": a["description"],
            "category": a.get("category", "action"),
            "timestamp": now,
            "metadata": {
                "impact_dollars": impact,
                "effort": a.get("effort"),
                "confidence": a.get("confidence"),
            },
        })

    # Add causal narrative as a feed item if significant
    if drivers.get("drivers") and abs(drivers.get("change_pct", 0)) > 5:
        feed.append({
            "id": "causal-revenue",
            "feed_type": "causal",
            "severity": "negative" if drivers["change_amount"] < 0 else "positive",
            "priority": 4,
            "title": "Revenue change breakdown available",
            "message": drivers.get("narrative", ""),
            "category": "revenue",
            "timestamp": now,
            "metadata": {
                "change_pct": drivers["change_pct"],
                "driver_count": len(drivers["drivers"]),
            },
        })

    # Add missed revenue summary
    total_missed = missed.get("total_missed_revenue", 0)
    if total_missed > 100:
        feed.append({
            "id": "missed-revenue",
            "feed_type": "missed_revenue",
            "severity": "warning",
            "priority": 5,
            "title": f"{_sym(store_id)}{total_missed:,.0f} in missed revenue detected",
            "message": f"Identified {_sym(store_id)}{total_missed:,.0f} in potential lost revenue from refunds, churn, and stockout signals this period.",
            "category": "revenue",
            "timestamp": now,
            "metadata": {"total": total_missed},
        })

    # Sort by priority (lower = more urgent)
    feed.sort(key=lambda x: x["priority"])

    return feed
