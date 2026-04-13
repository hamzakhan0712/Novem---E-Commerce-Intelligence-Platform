from typing import Optional

from pydantic import BaseModel

from app.models.enums import DataType, ImportStatus, IndustryTemplate, MergeStrategy, SourceType

__all__ = ["DataType", "SourceType", "IndustryTemplate"]


# ── Column Mapping ──────────────────────────────────────────────────────


class ColumnMapping(BaseModel):
    source_column: str
    target_column: Optional[str] = None
    auto_mapped: bool
    data_type_hint: str


# ── File Upload & Preview ───────────────────────────────────────────────


class DataPreview(BaseModel):
    headers: list[str]
    rows: list[list]
    total_rows: int


class DetectedSchema(BaseModel):
    data_type: DataType
    confidence: float
    suggested_mappings: list[ColumnMapping]
    detected_template: IndustryTemplate


class UploadFileResponse(BaseModel):
    preview: DataPreview
    detection: DetectedSchema
    file_path: str
    file_hash: str
    mixed_types: Optional[list[str]] = None
    warnings: list[str] = []


# ── Quality Checks ──────────────────────────────────────────────────────


class HealthCheckDetail(BaseModel):
    check: str
    score: float
    weight: float
    issues: list[str]


# ── Import Requests & Responses ─────────────────────────────────────────


class ConfirmImportRequest(BaseModel):
    file_path: str
    store_id: str
    data_type: DataType
    mappings: list[ColumnMapping]
    has_header_row: bool = True
    selected_sheet: Optional[str] = None
    file_hash: Optional[str] = None
    merge_strategy: MergeStrategy = MergeStrategy.UPSERT


class ImportErrorDetail(BaseModel):
    row_number: Optional[int] = None
    column_name: Optional[str] = None
    error_type: str
    error_detail: str
    original_value: Optional[str] = None


class MergeResult(BaseModel):
    rows_new: int
    rows_updated: int
    rows_skipped: int
    rows_dropped: int = 0
    total_processed: int


class ConfirmImportResponse(BaseModel):
    import_id: str
    store_id: str
    data_type: str
    health_score: int
    health_details: list[HealthCheckDetail]
    merge_result: MergeResult
    lineage_steps: int
    warnings: list[str] = []
    import_errors: list[ImportErrorDetail] = []
    detection_confidence: Optional[float] = None


class GoogleSheetsRequest(BaseModel):
    url: str
    sheet_name: Optional[str] = None
    sheet_names: Optional[list[str]] = None
    store_id: str
    data_type: Optional[DataType] = None


class DatabaseConnectionTestRequest(BaseModel):
    engine: str
    host: Optional[str] = None
    port: Optional[int] = None
    database: str
    username: Optional[str] = None
    password: Optional[str] = None


# ── Import History ──────────────────────────────────────────────────────


class ImportHistoryItem(BaseModel):
    id: str
    store_id: str
    data_type: str
    source_type: str
    source_name: Optional[str] = None
    row_count_raw: int
    row_count_new: int
    row_count_updated: int
    row_count_skipped: int
    health_score: int
    health_details: list[HealthCheckDetail]
    status: str
    error_message: Optional[str] = None
    imported_at: str
    duration_ms: Optional[int] = None


class ImportLineageStep(BaseModel):
    id: str
    step_order: int
    description: str
    rows_before: int
    rows_after: int
    timestamp: str


# ── Data Profiling ──────────────────────────────────────────────────────


class ColumnProfile(BaseModel):
    name: str
    dtype: str
    null_count: int
    null_pct: float
    unique_count: int
    min: Optional[str | int | float] = None
    max: Optional[str | int | float] = None
    mean: Optional[float] = None
    std: Optional[float] = None
    top_values: list[dict]


class DataProfileResponse(BaseModel):
    columns: list[ColumnProfile]
    row_count: int
    date_range: Optional[dict] = None


# ── Store Data Summary ──────────────────────────────────────────────────


class StoreDataSummary(BaseModel):
    store_id: str
    orders_count: int = 0
    customers_count: int = 0
    products_count: int = 0
    ad_spend_count: int = 0
    reviews_count: int = 0
    stock_levels_count: int = 0
    date_range: Optional[dict] = None
    last_import_at: Optional[str] = None
    total_imports: int = 0


# ── Schema Reference ───────────────────────────────────────────────────


class SchemaColumnInfo(BaseModel):
    column: str
    required: bool
    data_type: str
    default_value: Optional[str] = None
    example: str
    notes: str


class SchemaReferenceResponse(BaseModel):
    data_type: str
    columns: list[SchemaColumnInfo]


# ── Validation / Dry Run ───────────────────────────────────────────────


class ValidationIssue(BaseModel):
    column: str
    issue: str
    severity: str
    affected_rows: int = 0
    sample_rows: list[int] = []


class ValidateFileRequest(BaseModel):
    file_path: str
    data_type: Optional[DataType] = None
    mappings: Optional[list[ColumnMapping]] = None
    has_header_row: bool = True
    selected_sheet: Optional[str] = None


class ValidateFileResponse(BaseModel):
    data_type: str
    total_rows: int
    valid_rows: int
    droppable_rows: int
    readiness_score: int
    column_mapping_summary: dict[str, str]
    unmapped_columns: list[str]
    missing_required: list[str]
    missing_recommended: list[str]
    issues: list[ValidationIssue]
    clean_actions_preview: list[str]
    currency_preview: list[str] = []
    status_preview: list[str] = []


# ── Feature Readiness ──────────────────────────────────────────────────


class FeatureReadiness(BaseModel):
    feature: str
    description: str
    minimum_required: str
    current_value: str
    status: str
    detail: str


class DataReadinessResponse(BaseModel):
    features: list[FeatureReadiness]
