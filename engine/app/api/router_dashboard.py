"""
Dashboard API router — KPIs, trends, and summary data.
"""

import logging

from fastapi import APIRouter, Query, HTTPException

from app.models.common import ApiResponse
from app.services.dashboard.kpi_calculator import calculate_kpis
from app.services.dashboard.time_series import get_time_series
from app.services.dashboard.revenue_at_risk import calculate_revenue_at_risk
from app.services.quality.quality_score import get_store_quality_score
from app.core.database import get_sqlite_connection

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
logger = logging.getLogger(__name__)

VALID_PERIODS = {"7d", "14d", "30d", "60d", "90d", "6m", "12m"}
VALID_METRICS = {"revenue", "orders", "customers", "aov"}
VALID_GRANULARITIES = {"daily", "weekly", "monthly"}


def _validate_store(store_id: str) -> None:
    conn = get_sqlite_connection()
    row = conn.execute("SELECT id FROM stores WHERE id = ?", (store_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Store not found")


@router.get("/kpis")
def dashboard_kpis(
    store_id: str = Query(...),
    period: str = Query("30d"),
) -> ApiResponse:
    """Core KPI summary with period-over-period comparison."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        data = calculate_kpis(store_id, period)
    except Exception as exc:
        logger.error("KPI calculation failed for store %s: %s", store_id, exc)
        raise HTTPException(status_code=500, detail="Failed to calculate KPIs") from exc
    return ApiResponse(success=True, data=data)


@router.get("/trends")
def dashboard_trends(
    store_id: str = Query(...),
    metric: str = Query("revenue"),
    granularity: str = Query("daily"),
    period: str = Query("30d"),
) -> ApiResponse:
    """Time-series data for a specific metric."""
    _validate_store(store_id)
    if metric not in VALID_METRICS:
        raise HTTPException(status_code=400, detail=f"Invalid metric. Use one of: {', '.join(sorted(VALID_METRICS))}")
    if granularity not in VALID_GRANULARITIES:
        raise HTTPException(status_code=400, detail=f"Invalid granularity. Use one of: {', '.join(sorted(VALID_GRANULARITIES))}")
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        data = get_time_series(store_id, metric, granularity, period)
    except Exception as exc:
        logger.error("Trends query failed for store %s: %s", store_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load trends") from exc
    return ApiResponse(success=True, data=data)


@router.get("/summary")
def dashboard_summary(
    store_id: str = Query(...),
    period: str = Query("30d"),
) -> ApiResponse:
    """Combined response: KPIs + sparkline trend for initial dashboard load."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        kpis = calculate_kpis(store_id, period)
        trends = get_time_series(store_id, "revenue", "daily", period)
    except Exception as exc:
        logger.error("Dashboard summary failed for store %s: %s", store_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load dashboard summary") from exc

    return ApiResponse(success=True, data={"kpis": kpis, "trends": trends})


@router.get("/revenue-at-risk")
def revenue_at_risk(
    store_id: str = Query(...),
    period: str = Query("12m"),
    lookahead_days: int = Query(30, ge=7, le=365),
) -> ApiResponse:
    """Revenue at risk — future revenue likely to be lost from overdue customers."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        data = calculate_revenue_at_risk(store_id, period, lookahead_days)
    except Exception as exc:
        logger.error("Revenue at risk failed for store %s: %s", store_id, exc)
        raise HTTPException(status_code=500, detail="Failed to calculate revenue at risk") from exc
    return ApiResponse(success=True, data=data)


@router.get("/quality")
def data_quality(store_id: str = Query(...)) -> ApiResponse:
    """Store-level data quality score with component breakdown."""
    _validate_store(store_id)
    try:
        score = get_store_quality_score(store_id)
    except Exception as exc:
        logger.error("Quality score failed for store %s: %s", store_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load quality score") from exc
    return ApiResponse(success=True, data=score)
