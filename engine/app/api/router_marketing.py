"""
Marketing API router — Ad spend analytics, channel breakdown, campaign ranking.
"""

import logging

from fastapi import APIRouter, Query, HTTPException

from app.models.common import ApiResponse
from app.services.marketing.marketing_kpi import calculate_marketing_kpis
from app.services.marketing.channel_analyzer import get_channel_breakdown, get_channel_trends
from app.services.marketing.campaign_ranker import get_campaign_performance
from app.services.marketing.ad_stock_correlation import detect_wasted_spend, get_category_marketing_roi
from app.core.database import get_sqlite_connection

router = APIRouter(prefix="/marketing", tags=["marketing"])
logger = logging.getLogger(__name__)

VALID_PERIODS = {"7d", "14d", "30d", "60d", "90d", "6m", "12m"}
VALID_METRICS = {"spend", "revenue", "roas", "conversions"}
VALID_GRANULARITY = {"daily", "weekly", "monthly"}
VALID_CAMPAIGN_SORT = {"roas", "spend", "conversions", "revenue", "cpc", "ctr"}


def _validate_store(store_id: str) -> None:
    conn = get_sqlite_connection()
    row = conn.execute("SELECT id FROM stores WHERE id = ?", (store_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Store not found")


@router.get("/summary")
def marketing_summary(
    store_id: str = Query(...),
    period: str = Query("30d"),
) -> ApiResponse:
    """Marketing KPIs: spend, ROAS, CPC, CTR, CVR, CPA with period-over-period."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        data = calculate_marketing_kpis(store_id, period)
    except Exception as exc:
        logger.error("Marketing summary failed for store %s: %s", store_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load marketing summary") from exc
    return ApiResponse(success=True, data=data)


@router.get("/channels")
def marketing_channels(
    store_id: str = Query(...),
    period: str = Query("30d"),
) -> ApiResponse:
    """Per-channel performance breakdown."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        data = get_channel_breakdown(store_id, period)
    except Exception as exc:
        logger.error("Channel breakdown failed for store %s: %s", store_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load channel breakdown") from exc
    return ApiResponse(success=True, data=data)


@router.get("/trends")
def marketing_trends(
    store_id: str = Query(...),
    period: str = Query("30d"),
    granularity: str = Query("daily"),
    metric: str = Query("spend"),
) -> ApiResponse:
    """Time-series of ad spend metrics by channel."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")
    if granularity not in VALID_GRANULARITY:
        raise HTTPException(status_code=400, detail=f"Invalid granularity. Use one of: {', '.join(sorted(VALID_GRANULARITY))}")
    if metric not in VALID_METRICS:
        raise HTTPException(status_code=400, detail=f"Invalid metric. Use one of: {', '.join(sorted(VALID_METRICS))}")

    try:
        data = get_channel_trends(store_id, period, granularity, metric)
    except Exception as exc:
        logger.error("Marketing trends failed for store %s: %s", store_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load marketing trends") from exc
    return ApiResponse(success=True, data=data)


@router.get("/campaigns")
def marketing_campaigns(
    store_id: str = Query(...),
    period: str = Query("30d"),
    sort_by: str = Query("roas"),
    limit: int = Query(50, ge=1, le=200),
) -> ApiResponse:
    """Campaign performance ranked by chosen metric."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")
    if sort_by not in VALID_CAMPAIGN_SORT:
        raise HTTPException(status_code=400, detail=f"Invalid sort_by. Use one of: {', '.join(sorted(VALID_CAMPAIGN_SORT))}")

    try:
        data = get_campaign_performance(store_id, period, sort_by, limit)
    except Exception as exc:
        logger.error("Campaign ranking failed for store %s: %s", store_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load campaign performance") from exc
    return ApiResponse(success=True, data=data)


@router.get("/wasted-spend")
def marketing_wasted_spend(
    store_id: str = Query(...),
    period: str = Query("30d"),
) -> ApiResponse:
    """Detect campaigns advertising out-of-stock products."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        data = detect_wasted_spend(store_id, period)
    except Exception as exc:
        logger.error("Wasted spend detection failed for store %s: %s", store_id, exc)
        raise HTTPException(status_code=500, detail="Failed to detect wasted spend") from exc
    return ApiResponse(success=True, data=data)


@router.get("/category-roi")
def marketing_category_roi(
    store_id: str = Query(...),
    period: str = Query("30d"),
) -> ApiResponse:
    """Ad spend vs order revenue by product category."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        data = get_category_marketing_roi(store_id, period)
    except Exception as exc:
        logger.error("Category ROI failed for store %s: %s", store_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load category ROI") from exc
    return ApiResponse(success=True, data=data)
