"""
Products API router — Product analytics and category breakdown.
"""

import logging

from fastapi import APIRouter, Query, HTTPException

from app.models.common import ApiResponse
from app.services.products.product_analytics import (
    get_product_summary,
    get_top_products,
    get_category_breakdown,
    get_product_revenue_trend,
)
from app.services.products.basket_analysis import get_basket_analysis
from app.services.products.inventory_optimizer import get_inventory_analysis
from app.services.products.lifecycle_classifier import classify_product_lifecycle
from app.services.products.stock_forecast import forecast_stock_levels
from app.services.products.stockout_analyzer import analyze_stockout_impact
from app.core.database import get_sqlite_connection

router = APIRouter(prefix="/products", tags=["products"])
logger = logging.getLogger(__name__)

VALID_PERIODS = {"7d", "14d", "30d", "60d", "90d", "6m", "12m"}
VALID_SORT = {"revenue", "units"}


def _validate_store(store_id: str) -> None:
    conn = get_sqlite_connection()
    row = conn.execute("SELECT id FROM stores WHERE id = ?", (store_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Store not found")


@router.get("/summary")
def product_summary(
    store_id: str = Query(...),
    period: str = Query("30d"),
) -> ApiResponse:
    """Product overview: total sold, categories, units, revenue."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        data = get_product_summary(store_id, period)
    except Exception as exc:
        logger.error("Product summary failed for store %s: %s", store_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load product summary") from exc
    return ApiResponse(success=True, data=data)


@router.get("/top")
def product_top(
    store_id: str = Query(...),
    period: str = Query("30d"),
    sort_by: str = Query("revenue"),
    limit: int = Query(20, ge=1, le=100),
) -> ApiResponse:
    """Top products ranked by revenue or units sold."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")
    if sort_by not in VALID_SORT:
        raise HTTPException(status_code=400, detail=f"Invalid sort_by. Use one of: {', '.join(sorted(VALID_SORT))}")

    try:
        data = get_top_products(store_id, period, sort_by, limit)
    except Exception as exc:
        logger.error("Top products query failed for store %s: %s", store_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load top products") from exc
    return ApiResponse(success=True, data=data)


@router.get("/categories")
def product_categories(
    store_id: str = Query(...),
    period: str = Query("30d"),
) -> ApiResponse:
    """Revenue breakdown by product category."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        data = get_category_breakdown(store_id, period)
    except Exception as exc:
        logger.error("Category breakdown failed for store %s: %s", store_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load category breakdown") from exc
    return ApiResponse(success=True, data=data)


@router.get("/trend")
def product_revenue_trend(
    store_id: str = Query(...),
    period: str = Query("30d"),
) -> ApiResponse:
    """Product revenue and units time-series."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        data = get_product_revenue_trend(store_id, period)
    except Exception as exc:
        logger.error("Product trend query failed for store %s: %s", store_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load product trend data") from exc
    return ApiResponse(success=True, data=data)


@router.get("/lifecycle")
def product_lifecycle(
    store_id: str = Query(...),
    period: str = Query("6m"),
) -> ApiResponse:
    """Product lifecycle classification — Rising Star, Cash Cow, Fading Out, Dead Weight."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        data = classify_product_lifecycle(store_id, period)
    except Exception as exc:
        logger.error("Product lifecycle failed for store %s: %s", store_id, exc)
        raise HTTPException(status_code=500, detail="Failed to classify product lifecycle") from exc
    return ApiResponse(success=True, data=data)


@router.get("/basket")
def product_basket(
    store_id: str = Query(...),
    period: str = Query("90d"),
    min_support: float = Query(0.01, ge=0.001, le=0.5),
    min_confidence: float = Query(0.1, ge=0.01, le=1.0),
) -> ApiResponse:
    """Market basket analysis — find frequently co-purchased products."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        data = get_basket_analysis(store_id, period, min_support, min_confidence)
    except Exception as exc:
        logger.error("Basket analysis failed for store %s: %s", store_id, exc)
        raise HTTPException(status_code=500, detail="Failed to run basket analysis") from exc
    return ApiResponse(success=True, data=data)


@router.get("/inventory")
def product_inventory(
    store_id: str = Query(...),
    period: str = Query("90d"),
    service_level: float = Query(0.95, ge=0.8, le=0.99),
) -> ApiResponse:
    """Inventory optimization — reorder points, safety stock, EOQ."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        data = get_inventory_analysis(store_id, period, service_level)
    except Exception as exc:
        logger.error("Inventory analysis failed for store %s: %s", store_id, exc)
        raise HTTPException(status_code=500, detail="Failed to run inventory analysis") from exc
    return ApiResponse(success=True, data=data)


@router.get("/stock-forecast")
def product_stock_forecast(
    store_id: str = Query(...),
    period: str = Query("90d"),
) -> ApiResponse:
    """Forecast stock depletion — when will each product run out?"""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        data = forecast_stock_levels(store_id, period)
    except Exception as exc:
        logger.error("Stock forecast failed for store %s: %s", store_id, exc)
        raise HTTPException(status_code=500, detail="Failed to run stock forecast") from exc
    return ApiResponse(success=True, data=data)


@router.get("/stockout-impact")
def product_stockout_impact(
    store_id: str = Query(...),
    period: str = Query("90d"),
) -> ApiResponse:
    """Detect past stockout events and estimate revenue loss."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        data = analyze_stockout_impact(store_id, period)
    except Exception as exc:
        logger.error("Stockout impact analysis failed for store %s: %s", store_id, exc)
        raise HTTPException(status_code=500, detail="Failed to analyze stockout impact") from exc
    return ApiResponse(success=True, data=data)
