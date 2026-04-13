"""
Alerts API router — alert management and KPI threshold checks.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.models.alerts import CreateAlertRequest, MarkReadRequest
from app.models.common import ApiResponse, PaginatedData
from app.services.alerts.alert_service import (
    check_kpi_thresholds,
    create_alert,
    delete_alert,
    get_alerts,
    get_unread_count,
    mark_alerts_read,
    mark_all_read,
    _get_alert_thresholds,
)

router = APIRouter(prefix="/alerts", tags=["alerts"])
logger = logging.getLogger(__name__)


@router.get("")
def list_alerts(
    store_id: Optional[str] = Query(None),
    is_read: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ApiResponse:
    offset = (page - 1) * page_size
    alerts, total = get_alerts(
        store_id=store_id, is_read=is_read, limit=page_size, offset=offset
    )
    return ApiResponse(
        success=True,
        data=PaginatedData(
            items=[a.model_dump() for a in alerts],
            total=total,
            page=page,
            page_size=page_size,
        ),
    )


@router.get("/unread-count")
def unread_count(store_id: Optional[str] = Query(None)) -> ApiResponse:
    count = get_unread_count(store_id)
    return ApiResponse(success=True, data={"count": count})


@router.post("")
def create_new_alert(req: CreateAlertRequest) -> ApiResponse:
    alert = create_alert(
        store_id=req.store_id,
        module=req.module,
        severity=req.severity,
        title=req.title,
        message=req.message,
    )
    return ApiResponse(success=True, data=alert.model_dump())


@router.post("/mark-read")
def mark_read(req: MarkReadRequest) -> ApiResponse:
    updated = mark_alerts_read(req.alert_ids)
    return ApiResponse(success=True, data={"updated": updated})


@router.post("/mark-all-read")
def mark_all_alerts_read(store_id: Optional[str] = Query(None)) -> ApiResponse:
    updated = mark_all_read(store_id)
    return ApiResponse(success=True, data={"updated": updated})


@router.delete("/{alert_id}")
def remove_alert(alert_id: str) -> ApiResponse:
    deleted = delete_alert(alert_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Alert not found")
    return ApiResponse(success=True, data={"deleted": True})


@router.post("/check-thresholds")
def run_threshold_check(store_id: str = Query(...)) -> ApiResponse:
    """Run KPI threshold checks and create alerts for anomalies."""
    alerts = check_kpi_thresholds(store_id)
    return ApiResponse(
        success=True,
        data={
            "alerts_created": len(alerts),
            "alerts": [a.model_dump() for a in alerts],
        },
    )


class AlertThresholdsRequest(BaseModel):
    revenue_drop_pct: float | None = None
    order_drop_pct: float | None = None
    customer_drop_pct: float | None = None
    aov_spike_pct: float | None = None


@router.get("/thresholds")
def get_thresholds() -> ApiResponse:
    """Get current alert threshold settings."""
    return ApiResponse(success=True, data=_get_alert_thresholds())


@router.put("/thresholds")
def update_thresholds(req: AlertThresholdsRequest) -> ApiResponse:
    """Update alert threshold settings."""
    from app.core.database import get_sqlite_connection

    current = _get_alert_thresholds()
    updates = req.model_dump(exclude_none=True)
    current.update(updates)

    conn = get_sqlite_connection()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        ("alert_thresholds", json.dumps(current)),
    )
    conn.commit()
    return ApiResponse(success=True, data=current)
