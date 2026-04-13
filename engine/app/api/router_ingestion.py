"""
Ingestion API router — store-aware data import pipeline.

Flow: Upload → Detect → Preview → Confirm → Clean → Merge → Done
All data merges into the store's unified tables via UPSERT.
"""

import hashlib
import io
import json
import logging
import os
import tempfile
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from starlette.responses import StreamingResponse

from app.core.database import get_duckdb_connection, get_sqlite_connection
from app.core.rate_limiter import limiter
from app.models.common import ApiError, ApiResponse
from app.models.ingestion import (
    ColumnMapping,
    ConfirmImportRequest,
    ConfirmImportResponse,
    DataPreview,
    DataProfileResponse,
    DataReadinessResponse,
    DataType,
    DetectedSchema,
    FeatureReadiness,
    GoogleSheetsRequest,
    HealthCheckDetail,
    ImportErrorDetail,
    ImportHistoryItem,
    ImportLineageStep,
    MergeResult,
    SchemaColumnInfo,
    SchemaReferenceResponse,
    StoreDataSummary,
    UploadFileResponse,
    ValidateFileRequest,
    ValidateFileResponse,
    ValidationIssue,
)
from app.services.ingestion.channel_normalizer import normalize_channels
from app.services.ingestion.column_mapper import get_mapping_quality, map_columns
from app.services.ingestion.data_cleaner import clean_dataframe
from app.services.ingestion.file_parser import (
    parse_file,
    read_full_dataframe,
)
from app.services.ingestion.google_sheets import fetch_google_sheet
from app.services.ingestion.merge_engine import get_store_row_counts, merge_into_store, save_import_errors
from app.services.ingestion.pii_masker import mask_pii
from app.services.ingestion.quality_checker import run_quality_checks
from app.services.ingestion.sample_data import generate_sample_data
from app.services.ingestion.schema_detector import (
    CANONICAL_COLUMNS,
    detect_schema,
    detect_type_column,
    infer_mixed_types,
    split_by_type_column,
)
from app.services.ingestion.template_service import (
    PLATFORM_GUIDES,
    evaluate_feature_readiness,
    generate_template_csv,
    get_schema_reference,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingestion", tags=["ingestion"])

UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "novem_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ─── File Upload & Detection ───────────────────────────────────────────


@router.post("/upload-file")
@limiter.limit("30/minute")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    has_header_row: bool = Form(True),
    selected_sheet: str | None = Form(None),
) -> ApiResponse[UploadFileResponse]:
    """Upload a file, parse it, detect schema, and return preview + mappings."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".csv", ".tsv", ".txt", ".xlsx", ".xls"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {ext}",
        )

    file_id = uuid.uuid4().hex[:12]
    safe_name = f"{file_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    file_hash = hashlib.sha256(content).hexdigest()

    try:
        headers, rows, total_rows = parse_file(
            file_path, selected_sheet, has_header_row,
        )

        data_type, confidence, template = detect_schema(headers)
        suggested_mappings = map_columns(headers, data_type)

        # Check mapping quality — reject unmappable files early
        mapped_pct, unmapped = get_mapping_quality(headers, data_type)
        if mapped_pct < 0.15:
            # Try other data types to find a better fit
            best_type, best_pct = data_type, mapped_pct
            for dt in DataType:
                if dt == data_type:
                    continue
                pct, _ = get_mapping_quality(headers, dt)
                if pct > best_pct:
                    best_type, best_pct = dt, pct
            if best_pct >= 0.15:
                data_type = best_type
                confidence = best_pct
                suggested_mappings = map_columns(headers, data_type)
                mapped_pct = best_pct
            else:
                raise HTTPException(
                    status_code=422,
                    detail="Unable to map file columns to any known data type. "
                    f"Unmapped columns: {', '.join(unmapped[:10])}",
                )

        # Check for mixed-file (multiple data types in one file)
        mixed_types_detected: list[str] = []
        try:
            df_full = read_full_dataframe(file_path, selected_sheet, has_header_row)
            type_col = detect_type_column(df_full)
            if type_col:
                splits = split_by_type_column(df_full, type_col)
                if len(splits) >= 2:
                    mixed_types_detected = [dt.value for dt in splits.keys()]
        except Exception:
            pass  # Non-critical; proceed with single-type detection

        # Build warnings for low-confidence detection
        upload_warnings: list[str] = []
        if confidence < 0.6:
            upload_warnings.append(
                f"Low detection confidence ({confidence:.0%}). "
                f"Detected as '{data_type.value}' but may be incorrect. "
                "Please verify the data type selection before importing."
            )

        preview = DataPreview(
            headers=headers,
            rows=rows,
            total_rows=total_rows,
        )
        detection = DetectedSchema(
            data_type=data_type,
            confidence=round(confidence, 2),
            suggested_mappings=suggested_mappings,
            detected_template=template,
        )

        return ApiResponse(
            success=True,
            data=UploadFileResponse(
                preview=preview,
                detection=detection,
                file_path=file_path,
                file_hash=file_hash,
                mixed_types=mixed_types_detected if mixed_types_detected else None,
                warnings=upload_warnings,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("File upload error: %s", e)
        raise HTTPException(status_code=400, detail=str(e)) from e


# ─── Multi-File Upload & Detection ─────────────────────────────────────


@router.post("/upload-files")
async def upload_files(
    files: list[UploadFile] = File(...),
    has_header_row: bool = Form(True),
) -> ApiResponse[list[UploadFileResponse]]:
    """Upload multiple files, parse each, detect schema, and return previews + mappings."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 files per batch")

    results: list[UploadFileResponse] = []
    errors: list[str] = []

    for file in files:
        if not file.filename:
            errors.append("File with no filename skipped")
            continue

        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in (".csv", ".tsv", ".txt", ".xlsx", ".xls"):
            errors.append(f"Skipped {file.filename}: unsupported format {ext}")
            continue

        file_id = uuid.uuid4().hex[:12]
        safe_name = f"{file_id}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, safe_name)

        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        file_hash = hashlib.sha256(content).hexdigest()

        try:
            headers, rows, total_rows = parse_file(
                file_path, None, has_header_row,
            )

            data_type, confidence, template = detect_schema(headers)
            suggested_mappings = map_columns(headers, data_type)

            # Check mapping quality — skip unmappable files
            mapped_pct, unmapped = get_mapping_quality(headers, data_type)
            if mapped_pct < 0.15:
                best_type, best_pct = data_type, mapped_pct
                for dt in DataType:
                    if dt == data_type:
                        continue
                    pct, _ = get_mapping_quality(headers, dt)
                    if pct > best_pct:
                        best_type, best_pct = dt, pct
                if best_pct >= 0.15:
                    data_type = best_type
                    confidence = best_pct
                    suggested_mappings = map_columns(headers, data_type)
                else:
                    errors.append(
                        f"{file.filename}: Unable to map columns to any known data type"
                    )
                    continue

            preview = DataPreview(
                headers=headers,
                rows=rows,
                total_rows=total_rows,
            )
            detection = DetectedSchema(
                data_type=data_type,
                confidence=round(confidence, 2),
                suggested_mappings=suggested_mappings,
                detected_template=template,
            )

            results.append(UploadFileResponse(
                preview=preview,
                detection=detection,
                file_path=file_path,
                file_hash=file_hash,
            ))
        except Exception as e:
            logger.error("File upload error for %s: %s", file.filename, e)
            errors.append(f"Failed to parse {file.filename}: {str(e)}")

    if not results and errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    return ApiResponse(success=True, data=results)


# ─── Batch Confirm Import ──────────────────────────────────────────────


@router.post("/confirm-batch-import")
async def confirm_batch_import(
    items: list[ConfirmImportRequest],
    store_id: str = Query(...),
) -> ApiResponse[list[ConfirmImportResponse]]:
    """Confirm import for multiple files in a single request."""
    _validate_store_exists(store_id)

    if len(items) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 imports per batch")

    results: list[ConfirmImportResponse] = []
    errors: list[str] = []
    for idx, req in enumerate(items):
        req.store_id = store_id
        try:
            resp = await confirm_import(req)
            if resp.data:
                results.append(resp.data)
        except HTTPException as exc:
            error_msg = f"File {idx + 1} ({req.data_type.value}): {exc.detail}"
            logger.error("Batch import item failed: %s", error_msg)
            errors.append(error_msg)
        except Exception as exc:
            error_msg = f"File {idx + 1} ({req.data_type.value}): {exc}"
            logger.error("Batch import item unexpected error: %s", error_msg)
            errors.append(error_msg)

    if errors and not results:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    return ApiResponse(
        success=len(errors) == 0,
        data=results,
        error=ApiError(code="PARTIAL_IMPORT", detail="; ".join(errors)) if errors else None,
    )


# ─── Confirm Import (Main Pipeline) ────────────────────────────────────


@router.post("/confirm-import")
async def confirm_import(
    req: ConfirmImportRequest,
) -> ApiResponse[ConfirmImportResponse]:
    """Confirm import: map columns, clean, quality-check, and merge into store."""
    _validate_store_exists(req.store_id)

    start_time = time.monotonic()

    try:
        df = read_full_dataframe(
            req.file_path,
            req.selected_sheet,
            req.has_header_row,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot read file: {e}") from e

    import_id = str(uuid.uuid4())
    lineage_steps: list[dict] = []
    step_order = 0

    # Step 1: Parse
    initial_rows = len(df)
    step_order += 1
    lineage_steps.append(_lineage_entry(
        import_id, step_order,
        f"Parsed {initial_rows} rows from {os.path.basename(req.file_path)}",
        initial_rows, initial_rows,
    ))

    # Step 2: Pre-mapping transformations
    # Combine first_name + last_name before mapping (Shopify/WooCommerce exports)
    _name_variants = {"first_name", "firstname", "billing_first_name", "billing_firstname"}
    _last_variants = {"last_name", "lastname", "billing_last_name", "billing_lastname"}

    if req.data_type in (DataType.CUSTOMERS, DataType.ORDERS):
        first_col = next((c for c in df.columns if c.lower().replace(" ", "_") in _name_variants), None)
        last_col = next((c for c in df.columns if c.lower().replace(" ", "_") in _last_variants), None)

        target_field = "name_hash" if req.data_type == DataType.CUSTOMERS else "customer_name_hash"
        name_target = None
        for m in req.mappings:
            if m.target_column == target_field:
                name_target = m.source_column
                break

        if first_col and last_col:
            combined = (
                df[first_col].fillna("").astype(str) + " " + df[last_col].fillna("").astype(str)
            ).str.strip()
            combined = combined.replace("", None)
            if name_target and name_target in df.columns:
                null_mask = df[name_target].isna()
                df.loc[null_mask, name_target] = combined[null_mask]
            elif name_target == first_col:
                df[first_col] = combined
            else:
                df["_combined_name"] = combined

    # Step 3: Column mapping
    mapping_dict: dict[str, str] = {}
    for m in req.mappings:
        if m.target_column:
            mapping_dict[m.source_column] = m.target_column

    canonical_cols = CANONICAL_COLUMNS.get(req.data_type, [])
    rename_map = {}
    for src, tgt in mapping_dict.items():
        if src in df.columns and tgt in canonical_cols:
            rename_map[src] = tgt

    # If we created a combined name col and the target field wasn't mapped, map it
    target_name_col = "name_hash" if req.data_type == DataType.CUSTOMERS else "customer_name_hash"
    if "_combined_name" in df.columns and target_name_col not in rename_map.values():
        rename_map["_combined_name"] = target_name_col

    df = df.rename(columns=rename_map)
    for col in canonical_cols:
        if col not in df.columns:
            df[col] = None
    df = df[canonical_cols]

    step_order += 1
    lineage_steps.append(_lineage_entry(
        import_id, step_order,
        f"Mapped {len(rename_map)} source columns to canonical {req.data_type.value} schema",
        len(df), len(df),
    ))

    # Step 3: Remove exact duplicate rows
    rows_before = len(df)
    df = df.drop_duplicates()
    removed = rows_before - len(df)
    if removed > 0:
        step_order += 1
        lineage_steps.append(_lineage_entry(
            import_id, step_order,
            f"Removed {removed} duplicate rows",
            rows_before, len(df),
        ))

    # Step 4: Data cleaning
    df, clean_actions = clean_dataframe(df, req.data_type.value)
    if clean_actions:
        step_order += 1
        lineage_steps.append(_lineage_entry(
            import_id, step_order,
            f"Cleaned data: {'; '.join(clean_actions[:5])}",
            len(df), len(df),
        ))

    # Step 5: Channel normalization
    if "channel" in df.columns and df["channel"].notna().any():
        raw_channels = df["channel"].dropna().unique().tolist()
        channel_map = normalize_channels(raw_channels)
        df["channel"] = df["channel"].map(
            lambda v, cm=channel_map: cm.get(v, v) if pd.notna(v) else v,
        )
        normalized_count = sum(1 for k, v in channel_map.items() if k != v)
        if normalized_count > 0:
            step_order += 1
            lineage_steps.append(_lineage_entry(
                import_id, step_order,
                f"Normalized {normalized_count} channel values",
                len(df), len(df),
            ))

    # Step 6: PII masking
    col_map_for_pii = {col: col for col in df.columns}
    df, hashed_count = mask_pii(df, col_map_for_pii)
    if hashed_count > 0:
        step_order += 1
        lineage_steps.append(_lineage_entry(
            import_id, step_order,
            f"Hashed {hashed_count} PII values (SHA-256)",
            len(df), len(df),
        ))

    # Step 7: Quality check
    mapped_for_quality = {col: col for col in df.columns if col in canonical_cols}
    health_score, health_details = run_quality_checks(
        df, mapped_for_quality, req.data_type.value,
    )

    # Step 7.5: Compute line_item_index for orders (handles same SKU ordered twice)
    import_warnings: list[str] = []
    if req.data_type == DataType.ORDERS and "line_item_index" in df.columns:
        if "order_id" in df.columns and "product_id" in df.columns:
            df["line_item_index"] = df.groupby(["order_id", "product_id"]).cumcount()
            multi_items = (df["line_item_index"] > 0).sum()
            if multi_items > 0:
                import_warnings.append(
                    f"{multi_items} line items share the same order+product — "
                    "assigned line_item_index to preserve all rows."
                )
        else:
            df["line_item_index"] = 0

    # Step 8: Merge into store (UPSERT by default)
    # Snapshot current state for rollback before merging
    snapshot_id = None
    try:
        from app.services.ingestion.import_versioning import create_snapshot
        snapshot_id = create_snapshot(req.store_id, req.data_type.value, import_id)
    except Exception as exc:
        logger.warning("Pre-import snapshot failed (non-blocking): %s", exc)

    try:
        merge_result = merge_into_store(
            df=df,
            store_id=req.store_id,
            data_type=req.data_type.value,
            strategy=req.merge_strategy.value,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Unexpected merge error for store %s: %s", req.store_id, exc)
        raise HTTPException(
            status_code=500,
            detail=f"Import failed during merge: {exc}",
        ) from exc

    step_order += 1
    lineage_steps.append(_lineage_entry(
        import_id, step_order,
        f"Merged into store: {merge_result.rows_new} new, "
        f"{merge_result.rows_updated} updated, {merge_result.rows_skipped} skipped",
        len(df), merge_result.rows_new + merge_result.rows_updated,
    ))

    # Step 9: Save import history + lineage to SQLite
    duration_ms = int((time.monotonic() - start_time) * 1000)
    _save_import_history(
        import_id=import_id,
        store_id=req.store_id,
        data_type=req.data_type.value,
        source_type="file",
        source_name=os.path.basename(req.file_path),
        source_path=req.file_path,
        file_hash=req.file_hash,
        row_count_raw=initial_rows,
        merge_result=merge_result,
        health_score=health_score,
        health_details=health_details,
        schema_mapping=req.mappings,
        duration_ms=duration_ms,
    )
    _save_lineage(lineage_steps)

    # Precompute copilot context cache so AI understands new data immediately
    try:
        from app.services.copilot.context_cache import invalidate_cache as _inv_cache
        from app.services.copilot.context_cache import build_store_context as _build_ctx
        from app.services.copilot.copilot_service import clear_response_cache as _clear_resp
        _inv_cache(req.store_id)
        _clear_resp(req.store_id)
        _build_ctx(req.store_id)
    except Exception as exc:
        logger.warning("Post-import context cache build failed: %s", exc)

    return ApiResponse(
        success=True,
        data=ConfirmImportResponse(
            import_id=import_id,
            store_id=req.store_id,
            data_type=req.data_type.value,
            health_score=health_score,
            health_details=health_details,
            merge_result=merge_result,
            lineage_steps=len(lineage_steps),
            warnings=import_warnings,
        ),
    )


# ─── Import Snapshots / Rollback ────────────────────────────────────────


@router.get("/snapshots")
def get_snapshots(
    store_id: str = Query(...),
) -> ApiResponse:
    """List available import snapshots for a store."""
    _validate_store_exists(store_id)
    from app.services.ingestion.import_versioning import list_snapshots
    snapshots = list_snapshots(store_id)
    return ApiResponse(success=True, data=snapshots)


@router.post("/rollback")
def rollback_import(
    store_id: str = Query(...),
    snapshot_id: str = Query(...),
) -> ApiResponse:
    """Roll back store data to a previous import snapshot."""
    _validate_store_exists(store_id)
    from app.services.ingestion.import_versioning import rollback_to_snapshot
    try:
        result = rollback_to_snapshot(store_id, snapshot_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("Rollback failed: %s", exc)
        raise HTTPException(status_code=500, detail="Rollback failed. Data may be in an inconsistent state.")
    return ApiResponse(success=True, data=result)


@router.delete("/snapshots")
def delete_snapshot_endpoint(
    store_id: str = Query(...),
    snapshot_id: str = Query(...),
) -> ApiResponse:
    """Delete a specific import snapshot."""
    _validate_store_exists(store_id)
    from app.services.ingestion.import_versioning import delete_snapshot
    delete_snapshot(store_id, snapshot_id)
    return ApiResponse(success=True, data={"deleted": snapshot_id})


# ─── Cancel / Remove Uploaded File ──────────────────────────────────────


@router.delete("/cancel-file")
async def cancel_file(
    file_path: str = Query(...),
) -> ApiResponse[dict]:
    """Cancel / remove an uploaded file before import confirmation."""
    if not file_path.startswith(UPLOAD_DIR):
        raise HTTPException(status_code=400, detail="Invalid file path")

    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError as e:
            logger.warning("Could not delete uploaded file %s: %s", file_path, e)

    return ApiResponse(success=True, data={"removed": True})


# ─── Mixed-File Import ─────────────────────────────────────────────────


@router.post("/confirm-mixed-import")
async def confirm_mixed_import(
    req: ConfirmImportRequest,
) -> ApiResponse[list[ConfirmImportResponse]]:
    """Import a mixed-type file by splitting on the type/record_type column."""
    _validate_store_exists(req.store_id)

    try:
        df = read_full_dataframe(req.file_path, req.selected_sheet, req.has_header_row)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot read file: {e}") from e

    # Detect type column and split
    type_col = detect_type_column(df)
    if type_col:
        splits = split_by_type_column(df, type_col)
    else:
        splits = infer_mixed_types(df)

    if len(splits) < 2:
        raise HTTPException(
            status_code=400,
            detail="File does not contain multiple data types. Use standard import.",
        )

    results: list[ConfirmImportResponse] = []
    errors: list[str] = []

    for data_type, sub_df in splits.items():
        headers = list(sub_df.columns)
        suggested_mappings = map_columns(headers, data_type)

        try:
            resp = await _process_dataframe_import(
                df=sub_df.copy(),
                store_id=req.store_id,
                data_type=data_type.value,
                mappings=suggested_mappings,
                source_type="file_mixed",
                source_name=f"{os.path.basename(req.file_path)} ({data_type.value})",
                source_path=req.file_path,
            )
            if resp.data:
                results.append(resp.data)
        except Exception as exc:
            errors.append(f"{data_type.value}: {exc}")
            logger.error("Mixed import error for %s: %s", data_type.value, exc)

    if not results and errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    return ApiResponse(
        success=len(errors) == 0,
        data=results,
        error=ApiError(code="PARTIAL_IMPORT", detail="; ".join(errors)) if errors else None,
    )


# ─── Sample Data ────────────────────────────────────────────────────────


@router.post("/load-sample")
async def load_sample(
    store_id: str = Query(...),
) -> ApiResponse[ConfirmImportResponse]:
    """Load the built-in demo dataset (6 tables from pre-generated CSVs) into a store."""
    _validate_store_exists(store_id)

    try:
        start_time = time.monotonic()
        sample_data = generate_sample_data()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Sample CSV files could not be generated or found: {exc}",
        ) from exc
    except Exception as exc:
        logger.error("Failed to generate sample data: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate sample data: {exc}",
        ) from exc

    import_id = str(uuid.uuid4())
    total_new = 0
    total_updated = 0

    try:
        for table_name, df in sample_data.items():
            result = merge_into_store(df, store_id, table_name, strategy="upsert")
            total_new += result.rows_new
            total_updated += result.rows_updated
    except Exception as exc:
        logger.error("Failed to merge sample data into store %s: %s", store_id, exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to import sample data: {exc}",
        ) from exc

    health_details = [
        HealthCheckDetail(check="sample_data", score=95, weight=1.0, issues=[]),
    ]

    merge_result = MergeResult(
        rows_new=total_new,
        rows_updated=total_updated,
        rows_skipped=0,
        total_processed=total_new + total_updated,
    )

    duration_ms = int((time.monotonic() - start_time) * 1000)
    _save_import_history(
        import_id=import_id,
        store_id=store_id,
        data_type="all",
        source_type="sample",
        source_name="Sample E-Commerce Dataset (6 tables)",
        source_path="built-in",
        file_hash=None,
        row_count_raw=merge_result.total_processed,
        merge_result=merge_result,
        health_score=95,
        health_details=health_details,
        schema_mapping=[],
        duration_ms=duration_ms,
    )

    return ApiResponse(
        success=True,
        data=ConfirmImportResponse(
            import_id=import_id,
            store_id=store_id,
            data_type="all",
            health_score=95,
            health_details=health_details,
            merge_result=merge_result,
            lineage_steps=1,
        ),
    )


# ─── Google Sheets ──────────────────────────────────────────────────────


@router.post("/import-google-sheet")
async def import_google_sheet(
    req: GoogleSheetsRequest,
) -> ApiResponse[ConfirmImportResponse]:
    """Import data from a public Google Sheet into a store."""
    _validate_store_exists(req.store_id)

    try:
        df = fetch_google_sheet(req.url, req.sheet_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    headers = list(df.columns)
    data_type = req.data_type
    if not data_type:
        detected_type, _, _ = detect_schema(headers)
        data_type = detected_type

    suggested_mappings = map_columns(headers, data_type)

    return await _process_dataframe_import(
        df=df,
        store_id=req.store_id,
        data_type=data_type.value if hasattr(data_type, "value") else data_type,
        mappings=suggested_mappings,
        source_type="google_sheets",
        source_name="Google Sheet Import",
        source_path=req.url,
    )


@router.post("/import-google-sheets-batch")
async def import_google_sheets_batch(
    req: GoogleSheetsRequest,
) -> ApiResponse[list[ConfirmImportResponse]]:
    """Import multiple sheets from a Google Spreadsheet. If sheet_names is provided,
    imports each sheet individually; otherwise imports the default sheet."""
    _validate_store_exists(req.store_id)

    sheet_names = req.sheet_names or ([req.sheet_name] if req.sheet_name else [None])
    results: list[ConfirmImportResponse] = []

    for sheet_name in sheet_names:
        try:
            df = fetch_google_sheet(req.url, sheet_name)
        except Exception as e:
            logger.error("Failed to fetch sheet '%s': %s", sheet_name, e)
            continue

        if df.empty:
            continue

        headers = list(df.columns)
        data_type = req.data_type
        if not data_type:
            detected_type, _, _ = detect_schema(headers)
            data_type = detected_type

        suggested_mappings = map_columns(headers, data_type)

        resp = await _process_dataframe_import(
            df=df,
            store_id=req.store_id,
            data_type=data_type.value if hasattr(data_type, "value") else data_type,
            mappings=suggested_mappings,
            source_type="google_sheets",
            source_name=f"Google Sheet — {sheet_name or 'default'}",
            source_path=req.url,
        )
        if resp.data:
            results.append(resp.data)

    if not results:
        raise HTTPException(status_code=400, detail="No sheets were imported successfully")

    return ApiResponse(success=True, data=results)


# ─── Import History ────────────────────────────────────────────────────


@router.get("/imports")
async def list_imports(
    store_id: str = Query(...),
) -> ApiResponse[list[ImportHistoryItem]]:
    """List all imports for a store."""
    _validate_store_exists(store_id)

    conn = get_sqlite_connection()
    rows = conn.execute(
        "SELECT * FROM import_history WHERE store_id = ? ORDER BY imported_at DESC",
        (store_id,),
    ).fetchall()

    items = [_row_to_import_history(r) for r in rows]
    return ApiResponse(success=True, data=items)


@router.get("/imports/{import_id}")
async def get_import(import_id: str) -> ApiResponse[ImportHistoryItem]:
    """Get details of a specific import."""
    conn = get_sqlite_connection()
    row = conn.execute(
        "SELECT * FROM import_history WHERE id = ?", (import_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Import not found")
    return ApiResponse(success=True, data=_row_to_import_history(row))


@router.get("/imports/{import_id}/lineage")
async def get_import_lineage(
    import_id: str,
) -> ApiResponse[list[ImportLineageStep]]:
    """Get transform lineage for an import."""
    conn = get_sqlite_connection()
    rows = conn.execute(
        "SELECT * FROM import_lineage WHERE import_id = ? ORDER BY step_order",
        (import_id,),
    ).fetchall()

    steps = [
        ImportLineageStep(
            id=r["id"],
            step_order=r["step_order"],
            description=r["description"],
            rows_before=r["rows_before"] or 0,
            rows_after=r["rows_after"] or 0,
            timestamp=r["timestamp"],
        )
        for r in rows
    ]
    return ApiResponse(success=True, data=steps)


# ─── Store Data Summary & Profiling ────────────────────────────────────


@router.get("/store-summary")
async def get_store_summary(
    store_id: str = Query(...),
) -> ApiResponse[StoreDataSummary]:
    """Get data summary for a store across all tables."""
    _validate_store_exists(store_id)

    counts = get_store_row_counts(store_id)
    duck = get_duckdb_connection()

    # Get date range from orders
    date_range = None
    if counts.get("orders", 0) > 0:
        try:
            row = duck.execute(
                "SELECT MIN(order_date) as min_date, MAX(order_date) as max_date "
                "FROM orders WHERE store_id = ?",
                [store_id],
            ).fetchone()
            if row and row[0]:
                date_range = {
                    "min": str(row[0]),
                    "max": str(row[1]),
                }
        except Exception:
            pass

    # Get import stats
    conn = get_sqlite_connection()
    import_row = conn.execute(
        "SELECT COUNT(*) as cnt, MAX(imported_at) as last_at "
        "FROM import_history WHERE store_id = ? AND status = 'completed'",
        (store_id,),
    ).fetchone()

    return ApiResponse(
        success=True,
        data=StoreDataSummary(
            store_id=store_id,
            orders_count=counts.get("orders", 0),
            customers_count=counts.get("customers", 0),
            products_count=counts.get("products", 0),
            ad_spend_count=counts.get("ad_spend", 0),
            reviews_count=counts.get("reviews", 0),
            stock_levels_count=counts.get("stock_levels", 0),
            date_range=date_range,
            last_import_at=import_row["last_at"] if import_row else None,
            total_imports=import_row["cnt"] if import_row else 0,
        ),
    )


@router.get("/data-profile")
async def get_data_profile(
    store_id: str = Query(...),
    data_type: str = Query(...),
) -> ApiResponse[DataProfileResponse]:
    """Get data profiling results for a store's table."""
    _validate_store_exists(store_id)

    duck = get_duckdb_connection()
    valid_tables = {"orders", "customers", "products", "ad_spend", "reviews", "stock_levels"}
    if data_type not in valid_tables:
        raise HTTPException(status_code=400, detail=f"Invalid data type: {data_type}")

    try:
        df = duck.execute(
            f"SELECT * FROM {data_type} WHERE store_id = ?",  # noqa: S608
            [store_id],
        ).fetchdf()
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot query table {data_type}: {e}",
        ) from e

    if df.empty:
        return ApiResponse(
            success=True,
            data=DataProfileResponse(columns=[], row_count=0, date_range=None),
        )

    from app.models.ingestion import ColumnProfile

    columns: list[ColumnProfile] = []
    skip_cols = {"store_id", "created_at", "updated_at"}

    for col in df.columns:
        if col in skip_cols:
            continue

        series = df[col]
        null_count = int(series.isna().sum())
        null_pct = round(null_count / len(series) * 100, 2) if len(series) > 0 else 0
        unique_count = int(series.nunique())

        col_min = None
        col_max = None
        col_mean = None
        col_std = None
        top_values: list[dict] = []

        if pd.api.types.is_numeric_dtype(series):
            clean = series.dropna()
            if not clean.empty:
                col_min = float(clean.min())
                col_max = float(clean.max())
                col_mean = round(float(clean.mean()), 4)
                col_std = round(float(clean.std()), 4)
            dtype_str = "number"
        else:
            clean = series.dropna().astype(str)
            if not clean.empty:
                vc = clean.value_counts().head(5)
                top_values = [
                    {"value": str(v), "count": int(c)} for v, c in vc.items()
                ]
                col_min = str(clean.min()) if not clean.empty else None
                col_max = str(clean.max()) if not clean.empty else None

            if any(kw in col for kw in ("date", "time", "at")):
                dtype_str = "date"
            else:
                dtype_str = "string"

        columns.append(ColumnProfile(
            name=col,
            dtype=dtype_str,
            null_count=null_count,
            null_pct=null_pct,
            unique_count=unique_count,
            min=col_min,
            max=col_max,
            mean=col_mean,
            std=col_std,
            top_values=top_values,
        ))

    date_range = None
    date_cols = [c for c in df.columns if "date" in c or "time" in c]
    for dc in date_cols:
        parsed = pd.to_datetime(df[dc], errors="coerce").dropna()
        if not parsed.empty:
            date_range = {
                "min": parsed.min().isoformat(),
                "max": parsed.max().isoformat(),
            }
            break

    return ApiResponse(
        success=True,
        data=DataProfileResponse(
            columns=columns,
            row_count=len(df),
            date_range=date_range,
        ),
    )


@router.get("/check-duplicate")
async def check_duplicate(
    store_id: str = Query(...),
    file_hash: str = Query(...),
) -> ApiResponse[dict]:
    """Check if a file with the same hash has already been imported to this store."""
    conn = get_sqlite_connection()
    rows = conn.execute(
        "SELECT id, source_name, imported_at FROM import_history "
        "WHERE store_id = ? AND file_hash = ? AND status = 'completed' "
        "ORDER BY imported_at DESC",
        (store_id, file_hash),
    ).fetchall()

    if rows:
        existing = [
            {
                "id": r["id"],
                "source_name": r["source_name"],
                "imported_at": r["imported_at"],
            }
            for r in rows
        ]
        return ApiResponse(
            success=True,
            data={"is_duplicate": True, "existing_imports": existing},
        )

    return ApiResponse(
        success=True,
        data={"is_duplicate": False, "existing_imports": []},
    )


# ─── Template Download ─────────────────────────────────────────────────


@router.get("/template/{data_type}")
async def download_template(data_type: str) -> StreamingResponse:
    """Download a template CSV for the specified data type."""
    valid_types = {"orders", "customers", "products", "ad_spend", "reviews", "stock_levels"}
    if data_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid data type: {data_type}")

    csv_content = generate_template_csv(data_type)
    if not csv_content:
        raise HTTPException(status_code=500, detail="Failed to generate template")

    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="novem_template_{data_type}.csv"'},
    )


# ─── Schema Reference ──────────────────────────────────────────────────


@router.get("/schema-reference/{data_type}")
async def schema_reference(data_type: str) -> ApiResponse[SchemaReferenceResponse]:
    """Get schema reference (columns, types, requirements) for a data type."""
    valid_types = {"orders", "customers", "products", "ad_spend", "reviews", "stock_levels"}
    if data_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid data type: {data_type}")

    columns = get_schema_reference(data_type)

    return ApiResponse(
        success=True,
        data=SchemaReferenceResponse(
            data_type=data_type,
            columns=[SchemaColumnInfo(**col) for col in columns],
        ),
    )


@router.get("/schema-reference")
async def schema_reference_all() -> ApiResponse[list[SchemaReferenceResponse]]:
    """Get schema reference for all data types."""
    result: list[SchemaReferenceResponse] = []
    for dt in ("orders", "customers", "products", "ad_spend", "reviews", "stock_levels"):
        columns = get_schema_reference(dt)
        result.append(SchemaReferenceResponse(
            data_type=dt,
            columns=[SchemaColumnInfo(**col) for col in columns],
        ))
    return ApiResponse(success=True, data=result)


@router.get("/platform-guides")
async def platform_guides() -> ApiResponse[list[dict]]:
    """Get platform-specific export guides."""
    return ApiResponse(success=True, data=PLATFORM_GUIDES)


# ─── Pre-Upload Validation (Dry Run) ───────────────────────────────────


@router.post("/validate")
async def validate_file(
    req: ValidateFileRequest,
) -> ApiResponse[ValidateFileResponse]:
    """Dry-run validation: run the full pipeline without writing to DuckDB.
    Returns column mapping, issues, clean actions preview, and readiness score."""

    try:
        df = read_full_dataframe(req.file_path, req.selected_sheet, req.has_header_row)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot read file: {e}") from e

    total_rows = len(df)
    headers = list(df.columns)

    # Detect or use provided data type
    if req.data_type:
        data_type = req.data_type
    else:
        data_type, _, _ = detect_schema(headers)

    # Map columns
    if req.mappings:
        suggested_mappings = req.mappings
    else:
        suggested_mappings = map_columns(headers, data_type)

    canonical_cols = CANONICAL_COLUMNS.get(data_type, [])
    mapping_dict: dict[str, str] = {}
    for m in suggested_mappings:
        if m.target_column:
            mapping_dict[m.source_column] = m.target_column

    rename_map = {s: t for s, t in mapping_dict.items() if s in df.columns and t in canonical_cols}
    unmapped = [h for h in headers if h not in rename_map]

    # Apply mapping
    df = df.rename(columns=rename_map)
    for col in canonical_cols:
        if col not in df.columns:
            df[col] = None
    df = df[canonical_cols]

    # Check missing required/recommended
    from app.services.ingestion.merge_engine import TABLE_NOT_NULL_DEFAULTS
    not_null_map = TABLE_NOT_NULL_DEFAULTS.get(data_type.value, {})

    missing_required: list[str] = []
    missing_recommended: list[str] = []
    for col in canonical_cols:
        if col not in rename_map.values():
            if col in not_null_map and not_null_map[col] is None:
                missing_required.append(col)
            elif col in not_null_map:
                missing_recommended.append(col)

    # Run cleaning in dry mode — capture actions
    df_clean, clean_actions = clean_dataframe(df.copy(), data_type.value)

    # Build issues list
    issues: list[ValidationIssue] = []

    # Check for NULL values in required columns
    for col in not_null_map:
        if not_null_map[col] is None and col in df_clean.columns:
            null_mask = df_clean[col].isna() | (df_clean[col].astype(str).str.strip() == "")
            null_count = int(null_mask.sum())
            if null_count > 0:
                sample = null_mask[null_mask].head(5).index.tolist()
                issues.append(ValidationIssue(
                    column=col,
                    issue=f"{null_count} rows have missing/empty {col} (will be dropped)",
                    severity="error",
                    affected_rows=null_count,
                    sample_rows=[int(r) + 2 for r in sample],
                ))

    # Check for non-numeric values in numeric columns
    numeric_cols = [c for c in canonical_cols if c in df_clean.columns and any(
        kw in c for kw in ("price", "quantity", "amount", "spend", "stock", "cost", "impressions", "clicks", "conversions", "revenue", "rating", "lead_time")
    )]
    for col in numeric_cols:
        if col in df_clean.columns:
            non_numeric = pd.to_numeric(df_clean[col], errors="coerce")
            bad_count = int(non_numeric.isna().sum() - df_clean[col].isna().sum())
            if bad_count > 0:
                issues.append(ValidationIssue(
                    column=col,
                    issue=f"{bad_count} non-numeric values in {col}",
                    severity="warning",
                    affected_rows=bad_count,
                ))

    # Check date columns
    date_cols = [c for c in canonical_cols if c in df_clean.columns and any(
        kw in c for kw in ("date", "time")
    )]
    for col in date_cols:
        if col in df_clean.columns:
            parsed = pd.to_datetime(df_clean[col], errors="coerce", format="mixed")
            bad_count = int(parsed.isna().sum() - df_clean[col].isna().sum())
            if bad_count > 0:
                issues.append(ValidationIssue(
                    column=col,
                    issue=f"{bad_count} unparseable dates in {col}",
                    severity="warning",
                    affected_rows=bad_count,
                ))

    # Currency preview
    currency_preview: list[str] = []
    if "currency" in df_clean.columns:
        vals = df_clean["currency"].dropna().unique()
        currency_preview = [str(v) for v in vals[:10]]

    # Status preview
    status_preview: list[str] = []
    if "status" in df_clean.columns:
        vals = df_clean["status"].dropna().unique()
        status_preview = [str(v) for v in vals[:10]]

    # Count droppable rows (rows with missing required fields)
    droppable = 0
    for col in not_null_map:
        if not_null_map[col] is None and col in df_clean.columns:
            null_mask = df_clean[col].isna() | (df_clean[col].astype(str).str.strip() == "")
            droppable += int(null_mask.sum())
    # Cap at total rows (multiple columns can cause overlap)
    droppable = min(droppable, total_rows)

    valid_rows = total_rows - droppable
    readiness_score = max(0, min(100, int((valid_rows / max(total_rows, 1)) * 100)))

    return ApiResponse(
        success=True,
        data=ValidateFileResponse(
            data_type=data_type.value,
            total_rows=total_rows,
            valid_rows=valid_rows,
            droppable_rows=droppable,
            readiness_score=readiness_score,
            column_mapping_summary={s: t for s, t in rename_map.items()},
            unmapped_columns=unmapped,
            missing_required=missing_required,
            missing_recommended=missing_recommended,
            issues=issues,
            clean_actions_preview=clean_actions,
            currency_preview=currency_preview,
            status_preview=status_preview,
        ),
    )


# ─── Data Readiness Per Feature ─────────────────────────────────────────


@router.get("/data-readiness")
async def data_readiness(
    store_id: str = Query(...),
) -> ApiResponse[DataReadinessResponse]:
    """Check which analytics features are ready based on current store data."""
    _validate_store_exists(store_id)

    row_counts = get_store_row_counts(store_id)

    # Calculate date spans for time-series features
    date_spans: dict[str, int] = {}
    duck = get_duckdb_connection()
    for table, date_col in [("orders", "order_date"), ("ad_spend", "date")]:
        if row_counts.get(table, 0) > 0:
            try:
                row = duck.execute(
                    f"SELECT MIN({date_col}) as mn, MAX({date_col}) as mx "  # noqa: S608
                    f"FROM {table} WHERE store_id = ?",
                    [store_id],
                ).fetchone()
                if row and row[0] and row[1]:
                    span = (pd.Timestamp(row[1]) - pd.Timestamp(row[0])).days
                    date_spans[table] = max(span, 0)
            except Exception:
                pass

    features = evaluate_feature_readiness(row_counts, date_spans)

    return ApiResponse(
        success=True,
        data=DataReadinessResponse(
            features=[FeatureReadiness(**f) for f in features],
        ),
    )


# ─── Shared Pipeline for Non-File Sources ──────────────────────────────


async def _process_dataframe_import(
    *,
    df: pd.DataFrame,
    store_id: str,
    data_type: str,
    mappings: list[ColumnMapping],
    source_type: str,
    source_name: str,
    source_path: str,
) -> ApiResponse[ConfirmImportResponse]:
    """Shared pipeline: map → clean → normalize → mask → check → merge."""
    start_time = time.monotonic()
    import_id = str(uuid.uuid4())
    lineage_steps: list[dict] = []
    step_order = 0

    initial_rows = len(df)
    step_order += 1
    lineage_steps.append(_lineage_entry(
        import_id, step_order,
        f"Received {initial_rows} rows from {source_type}",
        initial_rows, initial_rows,
    ))

    # Column mapping
    canonical_cols = CANONICAL_COLUMNS.get(data_type, [])
    mapping_dict = {m.source_column: m.target_column for m in mappings if m.target_column}
    rename_map = {s: t for s, t in mapping_dict.items() if s in df.columns and t in canonical_cols}
    df = df.rename(columns=rename_map)
    for col in canonical_cols:
        if col not in df.columns:
            df[col] = None
    df = df[canonical_cols]

    step_order += 1
    lineage_steps.append(_lineage_entry(
        import_id, step_order,
        f"Mapped {len(rename_map)} columns to canonical {data_type} schema",
        len(df), len(df),
    ))

    # Dedup
    rows_before = len(df)
    df = df.drop_duplicates()
    removed = rows_before - len(df)
    if removed > 0:
        step_order += 1
        lineage_steps.append(_lineage_entry(
            import_id, step_order,
            f"Removed {removed} duplicate rows",
            rows_before, len(df),
        ))

    # Clean
    df, clean_actions = clean_dataframe(df, data_type)
    if clean_actions:
        step_order += 1
        lineage_steps.append(_lineage_entry(
            import_id, step_order,
            f"Cleaned data: {'; '.join(clean_actions[:5])}",
            len(df), len(df),
        ))

    # Channel normalization
    if "channel" in df.columns and df["channel"].notna().any():
        raw_channels = df["channel"].dropna().unique().tolist()
        channel_map = normalize_channels(raw_channels)
        df["channel"] = df["channel"].map(
            lambda v, cm=channel_map: cm.get(v, v) if pd.notna(v) else v,
        )

    # PII masking
    col_map_for_pii = {col: col for col in df.columns}
    df, hashed_count = mask_pii(df, col_map_for_pii)
    if hashed_count > 0:
        step_order += 1
        lineage_steps.append(_lineage_entry(
            import_id, step_order,
            f"Hashed {hashed_count} PII values (SHA-256)",
            len(df), len(df),
        ))

    # Quality check
    mapped_for_quality = {col: col for col in df.columns if col in canonical_cols}
    health_score, health_details = run_quality_checks(df, mapped_for_quality, data_type)

    # Merge into store
    merge_result = merge_into_store(df, store_id, data_type, strategy="upsert")

    step_order += 1
    lineage_steps.append(_lineage_entry(
        import_id, step_order,
        f"Merged: {merge_result.rows_new} new, {merge_result.rows_updated} updated",
        len(df), merge_result.rows_new + merge_result.rows_updated,
    ))

    duration_ms = int((time.monotonic() - start_time) * 1000)
    _save_import_history(
        import_id=import_id,
        store_id=store_id,
        data_type=data_type,
        source_type=source_type,
        source_name=source_name,
        source_path=source_path,
        file_hash=None,
        row_count_raw=initial_rows,
        merge_result=merge_result,
        health_score=health_score,
        health_details=health_details,
        schema_mapping=mappings,
        duration_ms=duration_ms,
    )
    _save_lineage(lineage_steps)

    # Precompute copilot context cache for mixed-import too
    try:
        from app.services.copilot.context_cache import invalidate_cache as _inv_cache
        from app.services.copilot.context_cache import build_store_context as _build_ctx
        from app.services.copilot.copilot_service import clear_response_cache as _clear_resp
        _inv_cache(store_id)
        _clear_resp(store_id)
        _build_ctx(store_id)
    except Exception as exc:
        logger.warning("Post-import context cache build failed: %s", exc)

    return ApiResponse(
        success=True,
        data=ConfirmImportResponse(
            import_id=import_id,
            store_id=store_id,
            data_type=data_type,
            health_score=health_score,
            health_details=health_details,
            merge_result=merge_result,
            lineage_steps=len(lineage_steps),
        ),
    )


# ─── Helpers ────────────────────────────────────────────────────────────


def _validate_store_exists(store_id: str) -> None:
    """Verify the store exists in SQLite, raise 404 if not."""
    conn = get_sqlite_connection()
    row = conn.execute(
        "SELECT id FROM stores WHERE id = ? AND is_active = 1", (store_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Store not found: {store_id}")


def _save_import_history(
    *,
    import_id: str,
    store_id: str,
    data_type: str,
    source_type: str,
    source_name: str,
    source_path: str | None,
    file_hash: str | None,
    row_count_raw: int,
    merge_result: MergeResult,
    health_score: int,
    health_details: list[HealthCheckDetail],
    schema_mapping: list[ColumnMapping],
    duration_ms: int,
) -> None:
    conn = get_sqlite_connection()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO import_history
           (id, store_id, data_type, source_type, source_name, source_path,
            file_hash, row_count_raw, row_count_new, row_count_updated,
            row_count_skipped, health_score, health_details, schema_mapping,
            status, imported_at, duration_ms)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?)""",
        (
            import_id, store_id, data_type, source_type, source_name,
            source_path, file_hash, row_count_raw,
            merge_result.rows_new, merge_result.rows_updated,
            merge_result.rows_skipped, health_score,
            json.dumps([d.model_dump() for d in health_details]),
            json.dumps([m.model_dump() for m in schema_mapping]),
            now, duration_ms,
        ),
    )
    conn.commit()


def _save_lineage(steps: list[dict]) -> None:
    conn = get_sqlite_connection()
    for step in steps:
        conn.execute(
            """INSERT INTO import_lineage
               (id, import_id, step_order, description, rows_before, rows_after, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                step["id"], step["import_id"], step["step_order"],
                step["description"], step["rows_before"],
                step["rows_after"], step["timestamp"],
            ),
        )
    conn.commit()


def _lineage_entry(
    import_id: str,
    step_order: int,
    description: str,
    rows_before: int,
    rows_after: int,
) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "import_id": import_id,
        "step_order": step_order,
        "description": description,
        "rows_before": rows_before,
        "rows_after": rows_after,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _row_to_import_history(row) -> ImportHistoryItem:
    health_details_raw = json.loads(row["health_details"] or "[]")
    return ImportHistoryItem(
        id=row["id"],
        store_id=row["store_id"],
        data_type=row["data_type"],
        source_type=row["source_type"],
        source_name=row["source_name"],
        row_count_raw=row["row_count_raw"],
        row_count_new=row["row_count_new"],
        row_count_updated=row["row_count_updated"],
        row_count_skipped=row["row_count_skipped"],
        health_score=row["health_score"],
        health_details=[HealthCheckDetail(**d) for d in health_details_raw],
        status=row["status"],
        error_message=row["error_message"],
        imported_at=row["imported_at"],
        duration_ms=row["duration_ms"],
    )
