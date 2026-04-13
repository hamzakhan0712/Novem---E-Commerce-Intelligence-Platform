export type DataType = 'orders' | 'customers' | 'products' | 'ad_spend' | 'reviews' | 'stock_levels';
export type SourceType = 'file' | 'google_sheets' | 'sample' | 'shopify_api' | 'google_sheets_api' | 'webhook' | 'postgresql';
export type IndustryTemplate = 'general' | 'fashion' | 'electronics' | 'home_garden' | 'beauty' | 'food' | 'health' | 'sports' | 'toys' | 'automotive';
export type HealthTier = 'healthy' | 'needs_review' | 'poor';

export interface ColumnMapping {
  source_column: string;
  target_column: string | null;
  auto_mapped: boolean;
  data_type_hint: string;
}

export interface DataPreview {
  headers: string[];
  rows: (string | number | null)[][];
  total_rows: number;
}

export interface DetectedSchema {
  data_type: DataType;
  confidence: number;
  suggested_mappings: ColumnMapping[];
  detected_template: IndustryTemplate;
}

export type FileImportStatus = 'pending' | 'uploading' | 'ready' | 'importing' | 'success' | 'error' | 'cancelled';

export interface UploadFileResponse {
  preview: DataPreview;
  detection: DetectedSchema;
  file_path: string;
  file_hash: string;
  mixed_types?: string[] | null;
  warnings?: string[];
}

export interface HealthCheckDetail {
  check: string;
  score: number;
  weight: number;
  issues: string[];
}

export interface GoogleSheetsRequest {
  url: string;
  sheet_name?: string;
  sheet_names?: string[];
  store_id: string;
}

export interface BatchFileItem {
  id: string;
  fileName: string;
  preview: DataPreview;
  detection: DetectedSchema;
  file_path: string;
  file_hash: string;
  status: FileImportStatus;
  error?: string | null;
  mixed_types?: string[] | null;
  warnings?: string[];
}

export interface DatabaseTableMapping {
  table: string;
  data_type: DataType;
}

export interface ImportHistoryItem {
  id: string;
  store_id: string;
  data_type: string;
  source_type: string;
  source_name: string | null;
  row_count_raw: number;
  row_count_new: number;
  row_count_updated: number;
  row_count_skipped: number;
  health_score: number;
  health_details: HealthCheckDetail[];
  status: string;
  error_message: string | null;
  imported_at: string;
  duration_ms: number | null;
}

export interface ImportLineageStep {
  id: string;
  step_order: number;
  description: string;
  rows_before: number;
  rows_after: number;
  timestamp: string;
}

export interface ColumnProfile {
  name: string;
  dtype: string;
  null_count: number;
  null_pct: number;
  unique_count: number;
  min: string | number | null;
  max: string | number | null;
  mean: number | null;
  std: number | null;
  top_values: { value: string; count: number }[];
}

export interface DataProfileResponse {
  columns: ColumnProfile[];
  row_count: number;
  date_range: { min: string; max: string } | null;
}

export function getHealthTier(score: number): HealthTier {
  if (score >= 80) return 'healthy';
  if (score >= 50) return 'needs_review';
  return 'poor';
}

export function getHealthColor(tier: HealthTier): string {
  switch (tier) {
    case 'healthy': return 'var(--novem-success)';
    case 'needs_review': return 'var(--novem-warning)';
    case 'poor': return 'var(--novem-error)';
  }
}

// ── Schema Reference ─────────────────────────────────────────────────

export interface SchemaColumnInfo {
  column: string;
  required: boolean;
  data_type: string;
  default_value: string | null;
  example: string;
  notes: string;
}

export interface SchemaReferenceResponse {
  data_type: string;
  columns: SchemaColumnInfo[];
}

// ── Validation / Dry Run ─────────────────────────────────────────────

export interface ValidationIssue {
  column: string;
  issue: string;
  severity: 'error' | 'warning' | 'info';
  affected_rows: number;
  sample_rows: number[];
}

export interface ValidateFileResponse {
  data_type: string;
  total_rows: number;
  valid_rows: number;
  droppable_rows: number;
  readiness_score: number;
  column_mapping_summary: Record<string, string>;
  unmapped_columns: string[];
  missing_required: string[];
  missing_recommended: string[];
  issues: ValidationIssue[];
  clean_actions_preview: string[];
  currency_preview: string[];
  status_preview: string[];
}

// ── Feature Readiness ────────────────────────────────────────────────

export interface FeatureReadiness {
  feature: string;
  description: string;
  minimum_required: string;
  current_value: string;
  status: 'ready' | 'warning' | 'not_ready';
  detail: string;
}

export interface DataReadinessResponse {
  features: FeatureReadiness[];
}

// ── Platform Guides ──────────────────────────────────────────────────

export interface PlatformGuide {
  platform: string;
  icon: string;
  steps: string;
}
