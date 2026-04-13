"""
Channel analyzer — Per-channel performance breakdown and time-series trends.
"""

import logging
from datetime import datetime, timedelta, timezone

from app.core.database import get_duckdb_connection

logger = logging.getLogger(__name__)

VALID_PERIODS = {"7d", "14d", "30d", "60d", "90d", "6m", "12m"}
VALID_GRANULARITY = {"daily", "weekly", "monthly"}


def _period_range(period: str) -> tuple[str, str]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    days = int(period[:-1]) * 30 if period.endswith("m") else int(period.rstrip("d"))
    start = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    end = now.strftime("%Y-%m-%d")
    return start, end


def get_channel_breakdown(store_id: str, period: str = "30d") -> list[dict]:
    """Per-channel aggregate KPIs."""
    conn = get_duckdb_connection()
    start, end = _period_range(period)

    rows = conn.execute(
        """
        SELECT
            channel,
            COALESCE(SUM(spend), 0)             AS spend,
            COALESCE(SUM(impressions), 0)        AS impressions,
            COALESCE(SUM(clicks), 0)             AS clicks,
            COALESCE(SUM(conversions), 0)        AS conversions,
            COALESCE(SUM(revenue_attributed), 0) AS revenue
        FROM ad_spend
        WHERE store_id = ?
          AND date >= ?
          AND date <= ?
        GROUP BY channel
        ORDER BY SUM(spend) DESC
        """,
        [store_id, start, end],
    ).fetchall()

    result = []
    for row in rows:
        ch, spend, imp, clicks, conv, rev = row
        result.append({
            "channel": ch,
            "spend": round(float(spend), 2),
            "impressions": int(imp),
            "clicks": int(clicks),
            "conversions": int(conv),
            "revenue": round(float(rev), 2),
            "roas": round(float(rev) / float(spend), 2) if float(spend) > 0 else 0.0,
            "cpc": round(float(spend) / int(clicks), 2) if int(clicks) > 0 else 0.0,
            "ctr": round((int(clicks) / int(imp)) * 100, 2) if int(imp) > 0 else 0.0,
            "cvr": round((int(conv) / int(clicks)) * 100, 2) if int(clicks) > 0 else 0.0,
        })
    return result


def get_channel_trends(
    store_id: str,
    period: str = "30d",
    granularity: str = "daily",
    metric: str = "spend",
) -> list[dict]:
    """Time-series of ad-spend metrics by channel, grouped by granularity."""
    conn = get_duckdb_connection()
    start, end = _period_range(period)

    if granularity == "weekly":
        date_trunc = "DATE_TRUNC('week', date)"
    elif granularity == "monthly":
        date_trunc = "DATE_TRUNC('month', date)"
    else:
        date_trunc = "date"

    rows = conn.execute(
        f"""
        SELECT
            CAST({date_trunc} AS DATE) AS bucket,
            channel,
            COALESCE(SUM(spend), 0)             AS spend,
            COALESCE(SUM(revenue_attributed), 0) AS revenue,
            COALESCE(SUM(conversions), 0)        AS conversions,
            COALESCE(SUM(impressions), 0)        AS impressions,
            COALESCE(SUM(clicks), 0)             AS clicks
        FROM ad_spend
        WHERE store_id = ?
          AND date >= ?
          AND date <= ?
        GROUP BY bucket, channel
        ORDER BY bucket, channel
        """,
        [store_id, start, end],
    ).fetchall()

    result = []
    for row in rows:
        bucket, ch, spend, rev, conv, imp, clicks = row
        spend_f = float(spend)
        rev_f = float(rev)
        roas = round(rev_f / spend_f, 2) if spend_f > 0 else 0.0
        ctr = round((int(clicks) / int(imp)) * 100, 2) if int(imp) > 0 else 0.0

        result.append({
            "date": str(bucket),
            "channel": ch,
            "spend": round(spend_f, 2),
            "revenue": round(rev_f, 2),
            "roas": roas,
            "conversions": int(conv),
            "impressions": int(imp),
            "clicks": int(clicks),
            "ctr": ctr,
        })
    return result
