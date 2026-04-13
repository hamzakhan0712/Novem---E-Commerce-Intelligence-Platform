"""
Email alerts API router — send digests, manage SMTP config, view history.
"""

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr

from app.models.common import ApiResponse
from app.services.alerts.email_service import (
    get_email_config,
    get_email_history,
    save_email_config,
    send_anomaly_digest,
    test_email_connection,
)
from app.core.database import get_sqlite_connection

router = APIRouter(prefix="/email", tags=["email"])
logger = logging.getLogger(__name__)


def _validate_store(store_id: str) -> None:
    conn = get_sqlite_connection()
    row = conn.execute("SELECT id FROM stores WHERE id = ?", (store_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Store not found")


class EmailConfigRequest(BaseModel):
    smtp_host: str
    smtp_port: int = 587
    smtp_user: str
    smtp_password: str
    from_name: str = "NOVEM"
    from_email: str
    use_tls: bool = True


class SendDigestRequest(BaseModel):
    store_id: str
    recipient_email: str
    period: str = "7d"


@router.get("/config")
def email_config() -> ApiResponse:
    """Get current email configuration (password masked)."""
    try:
        config = get_email_config()
    except Exception as exc:
        logger.error("Failed to load email config: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load email configuration") from exc
    return ApiResponse(success=True, data=config)


@router.post("/config")
def save_config(req: EmailConfigRequest) -> ApiResponse:
    """Save SMTP email configuration."""
    try:
        result = save_email_config(
            smtp_host=req.smtp_host,
            smtp_port=req.smtp_port,
            smtp_user=req.smtp_user,
            smtp_password=req.smtp_password,
            from_name=req.from_name,
            from_email=req.from_email,
            use_tls=req.use_tls,
        )
    except Exception as exc:
        logger.error("Failed to save email config: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to save email configuration") from exc
    return ApiResponse(success=True, data=result)


@router.post("/test")
def test_connection() -> ApiResponse:
    """Test SMTP connection without sending an email."""
    try:
        result = test_email_connection()
    except Exception as exc:
        logger.error("Email test failed: %s", exc)
        raise HTTPException(status_code=500, detail="Email connection test failed") from exc
    return ApiResponse(success=True, data=result)


@router.post("/send-digest")
def send_digest(req: SendDigestRequest) -> ApiResponse:
    """Send an anomaly digest email for a store."""
    _validate_store(req.store_id)

    try:
        result = send_anomaly_digest(req.store_id, req.recipient_email, req.period)
    except Exception as exc:
        logger.error("Failed to send digest: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to send email digest") from exc
    return ApiResponse(success=True, data=result)


@router.get("/history")
def email_history(
    store_id: str = Query(...),
    limit: int = Query(20, ge=1, le=100),
) -> ApiResponse:
    """Get recent email send history."""
    _validate_store(store_id)

    try:
        history = get_email_history(store_id, limit)
    except Exception as exc:
        logger.error("Failed to load email history: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load email history") from exc
    return ApiResponse(success=True, data=history)
