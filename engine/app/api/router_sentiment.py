"""Sentiment analysis API router."""

import logging

from fastapi import APIRouter, HTTPException, Query

from app.core.database import get_sqlite_connection
from app.models.common import ApiResponse
from app.services.sentiment.sentiment_service import (
    get_sentiment_summary,
    get_rating_breakdown,
    get_sentiment_trend,
    get_recent_reviews,
    get_products_needing_attention,
    get_top_keywords,
    analyze_unscored_reviews,
    get_sentiment_engine_status,
)

router = APIRouter(prefix="/sentiment", tags=["sentiment"])
logger = logging.getLogger(__name__)

VALID_PERIODS = {"7d", "14d", "30d", "90d", "6m", "12m"}


def _validate_store(store_id: str) -> None:
    conn = get_sqlite_connection()
    row = conn.execute("SELECT id FROM stores WHERE id = ?", (store_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Store not found")


@router.get("/summary")
def sentiment_summary(
    store_id: str = Query(...),
    period: str = Query("30d"),
) -> ApiResponse:
    """Sentiment KPIs with period-over-period comparison."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")
    try:
        data = get_sentiment_summary(store_id, period)
        return ApiResponse(success=True, data=data)
    except Exception as exc:
        logger.error("Sentiment summary failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load sentiment summary")


@router.get("/ratings")
def ratings_breakdown(
    store_id: str = Query(...),
    period: str = Query("30d"),
) -> ApiResponse:
    """Rating distribution with sentiment scores."""
    _validate_store(store_id)
    try:
        data = get_rating_breakdown(store_id, period)
        return ApiResponse(success=True, data=data)
    except Exception as exc:
        logger.error("Rating breakdown failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load rating breakdown")


@router.get("/trend")
def sentiment_trend(
    store_id: str = Query(...),
    period: str = Query("30d"),
) -> ApiResponse:
    """Daily sentiment trend over time."""
    _validate_store(store_id)
    try:
        data = get_sentiment_trend(store_id, period)
        return ApiResponse(success=True, data=data)
    except Exception as exc:
        logger.error("Sentiment trend failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load sentiment trend")


@router.get("/reviews")
def recent_reviews(
    store_id: str = Query(...),
    period: str = Query("30d"),
    limit: int = Query(50, ge=1, le=200),
) -> ApiResponse:
    """Recent reviews with sentiment labels."""
    _validate_store(store_id)
    try:
        data = get_recent_reviews(store_id, period, limit)
        return ApiResponse(success=True, data=data)
    except Exception as exc:
        logger.error("Recent reviews failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load reviews")


@router.get("/products")
def products_attention(
    store_id: str = Query(...),
    period: str = Query("30d"),
) -> ApiResponse:
    """Products with lowest sentiment scores."""
    _validate_store(store_id)
    try:
        data = get_products_needing_attention(store_id, period)
        return ApiResponse(success=True, data=data)
    except Exception as exc:
        logger.error("Products attention failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load product sentiment")


@router.get("/keywords")
def keywords(
    store_id: str = Query(...),
    period: str = Query("30d"),
) -> ApiResponse:
    """Top positive and negative keywords."""
    _validate_store(store_id)
    try:
        data = get_top_keywords(store_id, period)
        return ApiResponse(success=True, data=data)
    except Exception as exc:
        logger.error("Keyword extraction failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to extract keywords")


@router.post("/analyze")
def analyze_reviews(
    store_id: str = Query(...),
    limit: int = Query(100, ge=1, le=1000),
) -> ApiResponse:
    """Analyze unscored reviews and assign sentiment labels."""
    _validate_store(store_id)
    try:
        result = analyze_unscored_reviews(store_id, limit)
        return ApiResponse(success=True, data=result)
    except Exception as exc:
        logger.error("Review analysis failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to analyze reviews")


@router.get("/engine-status")
def engine_status() -> ApiResponse:
    """Report which sentiment analysis engine is active."""
    return ApiResponse(success=True, data=get_sentiment_engine_status())
