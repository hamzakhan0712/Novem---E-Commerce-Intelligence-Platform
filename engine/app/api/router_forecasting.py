"""
Forecasting API router — time-series forecasting.
"""

import logging

from fastapi import APIRouter, HTTPException, Query, Request

from app.core.database import get_sqlite_connection
from app.core.rate_limiter import limiter
from app.models.common import ApiResponse
from app.services.forecasting.forecast_service import generate_forecast, get_forecast_metrics_overview

router = APIRouter(prefix="/forecasting", tags=["forecasting"])
logger = logging.getLogger(__name__)

VALID_METRICS = {"revenue", "orders", "customers", "aov"}


def _validate_store(store_id: str) -> None:
    conn = get_sqlite_connection()
    row = conn.execute("SELECT id FROM stores WHERE id = ?", (store_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Store not found")


@router.get("")
@limiter.limit("30/minute")
def get_forecast(
    request: Request,
    store_id: str = Query(...),
    metric: str = Query("revenue"),
    horizon_days: int = Query(30, ge=7, le=90),
) -> ApiResponse:
    """Generate time-series forecast for a metric."""
    _validate_store(store_id)
    if metric not in VALID_METRICS:
        raise HTTPException(status_code=400, detail=f"Invalid metric. Use one of: {', '.join(sorted(VALID_METRICS))}")

    try:
        result = generate_forecast(store_id, metric, horizon_days)
    except Exception as exc:
        logger.error("Forecast generation failed: %s", exc)
        raise HTTPException(status_code=500, detail="Forecast generation failed. Ensure you have enough historical data.")

    return ApiResponse(success=True, data=result)


@router.get("/metrics")
def get_metrics_overview(
    store_id: str = Query(...),
    horizon_days: int = Query(30, ge=7, le=90),
) -> ApiResponse:
    """Quick forecast overview for all metrics."""
    _validate_store(store_id)

    try:
        results = get_forecast_metrics_overview(store_id, horizon_days)
    except Exception as exc:
        logger.error("Metrics overview failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate metrics overview.")

    return ApiResponse(success=True, data=results)
