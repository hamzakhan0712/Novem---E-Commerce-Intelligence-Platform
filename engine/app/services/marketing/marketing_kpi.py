"""
Marketing KPI calculator — Computes ad-spend metrics from DuckDB.
"""

import logging
from datetime import datetime, timedelta, timezone

from app.core.database import get_duckdb_connection

logger = logging.getLogger(__name__)

VALID_PERIODS = {"7d", "14d", "30d", "60d", "90d", "6m", "12m"}


def _parse_period(period: str) -> tuple[datetime, datetime, datetime, datetime]:
    if period not in VALID_PERIODS:
        period = "30d"

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    days = int(period[:-1]) * 30 if period.endswith("m") else int(period.rstrip("d"))

    current_end = now.replace(hour=23, minute=59, second=59)
    current_start = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0)
    prev_end = current_start - timedelta(seconds=1)
    prev_start = (current_start - timedelta(days=days)).replace(hour=0, minute=0, second=0)

    return current_start, current_end, prev_start, prev_end


def calculate_marketing_kpis(store_id: str, period: str = "30d") -> dict:
    """Core marketing KPIs with period-over-period comparison."""
    conn = get_duckdb_connection()
    current_start, current_end, prev_start, prev_end = _parse_period(period)

    def _query_period(start: datetime, end: datetime) -> dict:
        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(spend), 0)               AS total_spend,
                COALESCE(SUM(impressions), 0)          AS total_impressions,
                COALESCE(SUM(clicks), 0)               AS total_clicks,
                COALESCE(SUM(conversions), 0)          AS total_conversions,
                COALESCE(SUM(revenue_attributed), 0)   AS total_revenue
            FROM ad_spend
            WHERE store_id = ?
              AND date >= ?
              AND date <= ?
            """,
            [store_id, start.isoformat(), end.isoformat()],
        ).fetchone()

        if not row:
            return _empty()

        spend = float(row[0])
        impressions = int(row[1])
        clicks = int(row[2])
        conversions = int(row[3])
        revenue = float(row[4])

        return {
            "total_spend": round(spend, 2),
            "total_impressions": impressions,
            "total_clicks": clicks,
            "total_conversions": conversions,
            "total_revenue": round(revenue, 2),
            "roas": round(revenue / spend, 2) if spend > 0 else 0.0,
            "avg_cpc": round(spend / clicks, 2) if clicks > 0 else 0.0,
            "avg_ctr": round((clicks / impressions) * 100, 2) if impressions > 0 else 0.0,
            "avg_cvr": round((conversions / clicks) * 100, 2) if clicks > 0 else 0.0,
            "cpa": round(spend / conversions, 2) if conversions > 0 else 0.0,
        }

    current = _query_period(current_start, current_end)
    previous = _query_period(prev_start, prev_end)

    def _change_pct(curr: float, prev: float) -> float:
        if prev == 0:
            return 0.0 if curr == 0 else 100.0
        return round(((curr - prev) / prev) * 100, 1)

    return {
        "period": period,
        "current": current,
        "previous": previous,
        "changes": {
            "total_spend": _change_pct(current["total_spend"], previous["total_spend"]),
            "total_revenue": _change_pct(current["total_revenue"], previous["total_revenue"]),
            "roas": _change_pct(current["roas"], previous["roas"]),
            "avg_cpc": _change_pct(current["avg_cpc"], previous["avg_cpc"]),
            "avg_ctr": _change_pct(current["avg_ctr"], previous["avg_ctr"]),
            "avg_cvr": _change_pct(current["avg_cvr"], previous["avg_cvr"]),
            "cpa": _change_pct(current["cpa"], previous["cpa"]),
            "total_conversions": _change_pct(current["total_conversions"], previous["total_conversions"]),
        },
    }


def _empty() -> dict:
    return {
        "total_spend": 0.0,
        "total_impressions": 0,
        "total_clicks": 0,
        "total_conversions": 0,
        "total_revenue": 0.0,
        "roas": 0.0,
        "avg_cpc": 0.0,
        "avg_ctr": 0.0,
        "avg_cvr": 0.0,
        "cpa": 0.0,
    }
