"""
Customers API router — Customer analytics and segmentation.
"""

import logging

from fastapi import APIRouter, Query, HTTPException

from app.models.common import ApiResponse
from app.services.customers.customer_analytics import (
    get_customer_summary,
    get_top_customers,
    get_customer_segments,
    get_customer_growth,
)
from app.services.customers.customer_story import generate_customer_story
from app.services.customers.churn_predictor import get_churn_predictions
from app.services.customers.cohort_replay import get_cohort_replay
from app.services.customers.retention_analysis import (
    get_retention_curves,
    get_repeat_purchase_timing,
    get_churn_by_cohort,
)
from app.core.database import get_sqlite_connection

router = APIRouter(prefix="/customers", tags=["customers"])
logger = logging.getLogger(__name__)

VALID_PERIODS = {"7d", "14d", "30d", "60d", "90d", "6m", "12m"}


def _validate_store(store_id: str) -> None:
    conn = get_sqlite_connection()
    row = conn.execute("SELECT id FROM stores WHERE id = ?", (store_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Store not found")


@router.get("/summary")
def customer_summary(
    store_id: str = Query(...),
    period: str = Query("30d"),
) -> ApiResponse:
    """Customer overview: total, returning rate, average lifetime value."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        data = get_customer_summary(store_id, period)
    except Exception as exc:
        logger.error("Customer summary failed for store %s: %s", store_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load customer summary") from exc
    return ApiResponse(success=True, data=data)


@router.get("/top")
def customer_top(
    store_id: str = Query(...),
    period: str = Query("30d"),
    limit: int = Query(20, ge=1, le=100),
) -> ApiResponse:
    """Top customers ranked by total spend."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        data = get_top_customers(store_id, period, limit)
    except Exception as exc:
        logger.error("Top customers query failed for store %s: %s", store_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load top customers") from exc
    return ApiResponse(success=True, data=data)


@router.get("/segments")
def customer_segments(
    store_id: str = Query(...),
    period: str = Query("30d"),
) -> ApiResponse:
    """Customer spend segmentation: VIP, Regular, Low-spend."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        data = get_customer_segments(store_id, period)
    except Exception as exc:
        logger.error("Customer segments query failed for store %s: %s", store_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load customer segments") from exc
    return ApiResponse(success=True, data=data)


@router.get("/growth")
def customer_growth(
    store_id: str = Query(...),
    period: str = Query("30d"),
) -> ApiResponse:
    """Customer growth trend — new vs returning customers per day."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        data = get_customer_growth(store_id, period)
    except Exception as exc:
        logger.error("Customer growth query failed for store %s: %s", store_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load customer growth data") from exc
    return ApiResponse(success=True, data=data)


@router.get("/story")
def customer_story(
    store_id: str = Query(...),
    customer_id: str = Query(...),
) -> ApiResponse:
    """Generate a plain-language narrative about a customer's journey."""
    _validate_store(store_id)

    try:
        data = generate_customer_story(store_id, customer_id)
    except Exception as exc:
        logger.error("Customer story failed for %s/%s: %s", store_id, customer_id, exc)
        raise HTTPException(status_code=500, detail="Failed to generate customer story") from exc
    return ApiResponse(success=True, data=data)


@router.get("/cohort-replay")
def cohort_replay(
    store_id: str = Query(...),
    replay_month: str | None = Query(None),
    max_months: int = Query(12, ge=3, le=24),
) -> ApiResponse:
    """Cohort Replay — time-travel customer retention cohorts."""
    _validate_store(store_id)

    try:
        data = get_cohort_replay(store_id, replay_month, max_months)
    except Exception as exc:
        logger.error("Cohort replay failed for store %s: %s", store_id, exc)
        raise HTTPException(status_code=500, detail="Failed to generate cohort replay") from exc
    return ApiResponse(success=True, data=data)


@router.get("/churn")
def customer_churn(
    store_id: str = Query(...),
    period: str = Query("12m"),
    horizon_days: int = Query(90, ge=7, le=365),
) -> ApiResponse:
    """Predict customer churn risk using BG/NBD model."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        data = get_churn_predictions(store_id, period, horizon_days)
    except Exception as exc:
        logger.error("Churn prediction failed for store %s: %s", store_id, exc)
        raise HTTPException(status_code=500, detail="Failed to generate churn predictions") from exc
    return ApiResponse(success=True, data=data)


@router.get("/retention/curves")
def retention_curves(store_id: str = Query(...)) -> ApiResponse:
    """Averaged retention curves across all cohorts."""
    _validate_store(store_id)
    try:
        data = get_retention_curves(store_id)
        return ApiResponse(success=True, data=data)
    except Exception as exc:
        logger.error("Retention curves failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to compute retention curves")


@router.get("/retention/repeat-timing")
def repeat_timing(store_id: str = Query(...)) -> ApiResponse:
    """Distribution of days between first and second purchase."""
    _validate_store(store_id)
    try:
        data = get_repeat_purchase_timing(store_id)
        return ApiResponse(success=True, data=data)
    except Exception as exc:
        logger.error("Repeat timing failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to compute repeat timing")


@router.get("/retention/churn-by-cohort")
def churn_by_cohort(store_id: str = Query(...)) -> ApiResponse:
    """Monthly churn rate per cohort."""
    _validate_store(store_id)
    try:
        data = get_churn_by_cohort(store_id)
        return ApiResponse(success=True, data=data)
    except Exception as exc:
        logger.error("Churn by cohort failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to compute cohort churn")
