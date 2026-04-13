"""
Export API router — CSV export and summary reports.
"""

import logging
import os

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse

from app.core.database import get_sqlite_connection
from app.core.rate_limiter import limiter
from app.models.common import ApiResponse
from app.models.export import ExportRequest, NarrativeReportRequest
from app.services.export.export_service import (
    create_backup,
    export_bulk_csv,
    export_to_csv,
    export_to_parquet,
    generate_summary_report,
    get_export_row_count,
)
from app.services.export.report_builder import build_report
from app.services.export.pdf_generator import generate_pdf

router = APIRouter(prefix="/export", tags=["export"])
logger = logging.getLogger(__name__)

VALID_TYPES = {"orders", "customers", "products", "ad_spend", "reviews"}
VALID_PERIODS = {"7d", "14d", "30d", "60d", "90d", "6m", "12m"}


def _validate_store(store_id: str) -> None:
    conn = get_sqlite_connection()
    row = conn.execute("SELECT id FROM stores WHERE id = ?", (store_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Store not found")


@router.get("/preview")
def export_preview(
    store_id: str = Query(...),
    data_type: str = Query(...),
) -> ApiResponse:
    """Get row count preview before exporting."""
    _validate_store(store_id)
    if data_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid data_type. Use one of: {', '.join(sorted(VALID_TYPES))}")

    row_count = get_export_row_count(store_id, data_type)
    return ApiResponse(success=True, data={"data_type": data_type, "row_count": row_count})


@router.post("/csv")
def export_csv(req: ExportRequest) -> FileResponse:
    """Export store data as CSV file download."""
    _validate_store(req.store_id)
    if req.data_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid data_type. Use one of: {', '.join(sorted(VALID_TYPES))}")

    try:
        filepath, row_count = export_to_csv(req.store_id, req.data_type, req.limit)
    except Exception as exc:
        logger.error("Export failed: %s", exc)
        raise HTTPException(status_code=500, detail="Export failed. Please try again.")

    filename = os.path.basename(filepath)
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="text/csv",
        headers={"X-Row-Count": str(row_count)},
    )


@router.get("/report")
def summary_report(
    store_id: str = Query(...),
    period: str = Query("30d"),
) -> ApiResponse:
    """Generate a summary report with key metrics."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        report = generate_summary_report(store_id, period)
    except Exception as exc:
        logger.error("Report generation failed: %s", exc)
        raise HTTPException(status_code=500, detail="Report generation failed.")

    return ApiResponse(success=True, data=report)


@router.post("/narrative-report")
def narrative_report(req: NarrativeReportRequest) -> FileResponse:
    """Generate a full narrative BI report as a PDF download."""
    _validate_store(req.store_id)

    try:
        report_data = build_report(req.store_id, req.period, req.mode)
    except Exception as exc:
        logger.error("Narrative report build failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to build report data.")

    try:
        filepath = generate_pdf(report_data)
    except Exception as exc:
        logger.error("PDF generation failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate PDF.")

    import os
    filename = os.path.basename(filepath)
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/pdf",
    )


@router.post("/bulk-csv")
@limiter.limit("10/minute")
def bulk_csv_export(
    request: Request,
    store_id: str = Query(...),
) -> FileResponse:
    """Export all data tables as a single ZIP of CSVs."""
    _validate_store(store_id)
    try:
        zip_path, counts = export_bulk_csv(store_id)
    except Exception as exc:
        logger.error("Bulk export failed: %s", exc)
        raise HTTPException(status_code=500, detail="Bulk export failed.")

    filename = os.path.basename(zip_path)
    return FileResponse(
        path=zip_path,
        filename=filename,
        media_type="application/zip",
        headers={"X-Table-Counts": str(counts)},
    )


@router.post("/parquet")
@limiter.limit("10/minute")
def export_parquet(request: Request, req: ExportRequest) -> FileResponse:
    """Export store data as Parquet file download."""
    _validate_store(req.store_id)
    if req.data_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid data_type. Use one of: {', '.join(sorted(VALID_TYPES))}")

    try:
        filepath, row_count = export_to_parquet(req.store_id, req.data_type)
    except Exception as exc:
        logger.error("Parquet export failed: %s", exc)
        raise HTTPException(status_code=500, detail="Parquet export failed.")

    filename = os.path.basename(filepath)
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/octet-stream",
        headers={"X-Row-Count": str(row_count)},
    )


@router.post("/backup")
@limiter.limit("5/minute")
def create_full_backup(
    request: Request,
    store_id: str = Query(...),
) -> FileResponse:
    """Create a full backup of all store data + metadata as a ZIP."""
    _validate_store(store_id)
    try:
        zip_path, summary = create_backup(store_id)
    except Exception as exc:
        logger.error("Backup failed: %s", exc)
        raise HTTPException(status_code=500, detail="Backup creation failed.")

    filename = os.path.basename(zip_path)
    return FileResponse(
        path=zip_path,
        filename=filename,
        media_type="application/zip",
    )
