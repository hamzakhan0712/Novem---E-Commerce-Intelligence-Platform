"""
Campaign ranker — Rank campaigns by various marketing metrics.
"""

import logging
from datetime import datetime, timedelta, timezone

from app.core.database import get_duckdb_connection

logger = logging.getLogger(__name__)

VALID_PERIODS = {"7d", "14d", "30d", "60d", "90d", "6m", "12m"}
VALID_SORT = {"roas", "spend", "conversions", "revenue", "cpc", "ctr"}


def get_campaign_performance(
    store_id: str,
    period: str = "30d",
    sort_by: str = "roas",
    limit: int = 50,
) -> list[dict]:
    """All campaigns ranked by the chosen metric."""
    conn = get_duckdb_connection()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    days = int(period[:-1]) * 30 if period.endswith("m") else int(period.rstrip("d"))
    start = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    end = now.strftime("%Y-%m-%d")

    rows = conn.execute(
        """
        SELECT
            channel,
            campaign_name,
            COALESCE(SUM(spend), 0)             AS spend,
            COALESCE(SUM(impressions), 0)        AS impressions,
            COALESCE(SUM(clicks), 0)             AS clicks,
            COALESCE(SUM(conversions), 0)        AS conversions,
            COALESCE(SUM(revenue_attributed), 0) AS revenue,
            COUNT(DISTINCT date)                  AS active_days
        FROM ad_spend
        WHERE store_id = ?
          AND date >= ?
          AND date <= ?
        GROUP BY channel, campaign_name
        ORDER BY channel, campaign_name
        """,
        [store_id, start, end],
    ).fetchall()

    campaigns = []
    for row in rows:
        ch, name, spend, imp, clicks, conv, rev, active_days = row
        spend_f = float(spend)
        rev_f = float(rev)
        imp_i = int(imp)
        clicks_i = int(clicks)
        conv_i = int(conv)

        campaigns.append({
            "channel": ch,
            "campaign_name": name,
            "spend": round(spend_f, 2),
            "impressions": imp_i,
            "clicks": clicks_i,
            "conversions": conv_i,
            "revenue": round(rev_f, 2),
            "roas": round(rev_f / spend_f, 2) if spend_f > 0 else 0.0,
            "cpc": round(spend_f / clicks_i, 2) if clicks_i > 0 else 0.0,
            "ctr": round((clicks_i / imp_i) * 100, 2) if imp_i > 0 else 0.0,
            "cvr": round((conv_i / clicks_i) * 100, 2) if clicks_i > 0 else 0.0,
            "active_days": int(active_days),
        })

    sort_key = sort_by if sort_by in VALID_SORT else "roas"
    reverse = sort_key != "cpc"
    campaigns.sort(key=lambda c: c.get(sort_key, 0), reverse=reverse)

    return campaigns[:limit]
