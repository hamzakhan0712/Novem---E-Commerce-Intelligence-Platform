"""Competitive benchmarks API router."""

import logging

from fastapi import APIRouter, HTTPException, Query

from app.core.database import get_sqlite_connection
from app.models.common import ApiResponse
from app.services.benchmarks.benchmark_service import (
    get_benchmarks,
    get_benchmark_for_industry,
)

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])
logger = logging.getLogger(__name__)


def _validate_store(store_id: str) -> None:
    conn = get_sqlite_connection()
    row = conn.execute("SELECT id FROM stores WHERE id = ?", (store_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Store not found")


@router.get("/compare")
def compare_benchmarks(store_id: str = Query(...)) -> ApiResponse:
    """Compare store KPIs against industry benchmarks."""
    _validate_store(store_id)
    try:
        data = get_benchmarks(store_id)
        return ApiResponse(success=True, data=data)
    except Exception as exc:
        logger.error("Benchmark comparison failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to compute benchmarks")


@router.get("/industry/{industry}")
def industry_benchmarks(industry: str) -> ApiResponse:
    """Get raw benchmark values for a specific industry."""
    data = get_benchmark_for_industry(industry)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return ApiResponse(success=True, data=data)
