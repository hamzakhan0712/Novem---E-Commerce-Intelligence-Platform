# API Reference

This document covers every HTTP endpoint exposed by the NOVEM engine. The engine runs on `http://127.0.0.1:44945` by default.

---

## General Conventions

### Response Format

Every endpoint returns this shape:

```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

On error:
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "detail": "Human-readable message"
  }
}
```

### Pagination

Paginated endpoints accept `page` and `page_size` query params and return:

```json
{
  "data": [ ... ],
  "total": 1250,
  "page": 1,
  "pageSize": 50
}
```

### Authentication

Most endpoints require a valid session token in the request headers. The `/health`, `/auth/*`, and `/webhooks/*` endpoints are exempt.

### Common Query Parameters

- `store_id` (UUID) — Required on almost all data endpoints. Identifies which store's data to query.
- `period` (string) — Time period filter. Values: `7d`, `30d`, `90d`, `6m`, `12m`, `all`.

---

## Health

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Engine health check — returns status, uptime, database connectivity, and Ollama status |

---

## Auth (11 endpoints)

User authentication and profile management for the single-user desktop app.

| Method | Path | Description |
|---|---|---|
| `GET` | `/auth/status` | Check if profile is set up, return user info + password policy |
| `POST` | `/auth/setup` | First-time profile creation (name, email, password, security Q&A) |
| `POST` | `/auth/login` | Verify password and create session token |
| `POST` | `/auth/auto-login` | Create session without password (for 'never' password policy) |
| `POST` | `/auth/verify` | Check if a session token is still valid |
| `POST` | `/auth/lock` | Invalidate all sessions (locks the app) |
| `PATCH` | `/auth/profile` | Update profile fields (not password) |
| `POST` | `/auth/change-password` | Change password (requires current password) |
| `GET` | `/auth/security-question` | Get the stored security question for forgot-password flow |
| `POST` | `/auth/forgot-password` | Verify security answer, returns a reset token |
| `POST` | `/auth/reset-password` | Use reset token to set a new password |

**Rate Limiting**: Login is limited to 5 attempts per 15-minute window. Exceeding this returns HTTP 429.

---

## Dashboard (5 endpoints)

Core business KPIs and trend data.

| Method | Path | Params | Description |
|---|---|---|---|
| `GET` | `/dashboard/kpis` | `store_id`, `period` | 10 KPIs: revenue, orders, customers, AOV, repeat rate, new vs returning, refund rate, avg items/order, revenue/customer, churn proxy. Includes period-over-period comparison. |
| `GET` | `/dashboard/trends` | `store_id`, `metric`, `granularity`, `period` | Time-series data points for a specific metric. Granularity: `day`, `week`, `month`. |
| `GET` | `/dashboard/summary` | `store_id`, `period` | Combined KPIs with sparkline trend data in a single call |
| `GET` | `/dashboard/revenue-at-risk` | `store_id`, `period`, `lookahead_days` | Identifies overdue customers and estimates future revenue at risk |
| `GET` | `/dashboard/quality` | `store_id` | Data quality score breakdown across all imported datasets |

---

## Customers (7 endpoints)

Customer analytics, segmentation, and churn prediction.

| Method | Path | Params | Description |
|---|---|---|---|
| `GET` | `/customers/summary` | `store_id`, `period` | Overview: total customers, returning rate, avg lifetime value, total spend |
| `GET` | `/customers/top` | `store_id`, `period`, `limit` | Top customers ranked by total spend |
| `GET` | `/customers/segments` | `store_id`, `period` | Customer segmentation (VIP, Regular, Low-value) based on spend tiers |
| `GET` | `/customers/growth` | `store_id`, `period` | Customer growth trend — new vs returning over time |
| `GET` | `/customers/story` | `store_id`, `customer_id` | Generates a narrative story about a specific customer's journey |
| `GET` | `/customers/cohort-replay` | `store_id`, `replay_month`, `max_months` | Cohort retention analysis — shows how customer cohorts behave over time |
| `GET` | `/customers/churn` | `store_id`, `period`, `horizon_days` | Predicts churn risk for each customer using the BG/NBD model (lifetimes library) |

---

## Products (9 endpoints)

Product analytics, basket analysis, and inventory intelligence.

| Method | Path | Params | Description |
|---|---|---|---|
| `GET` | `/products/summary` | `store_id`, `period` | Overview: products sold, categories, total units, total revenue |
| `GET` | `/products/top` | `store_id`, `period`, `sort_by`, `limit` | Top products by revenue or units sold |
| `GET` | `/products/categories` | `store_id`, `period` | Revenue and order count by product category |
| `GET` | `/products/trend` | `store_id`, `period` | Product revenue and units over time |
| `GET` | `/products/lifecycle` | `store_id`, `period` | BCG-inspired lifecycle classification: Rising Star, Cash Cow, Fading, Dead Weight |
| `GET` | `/products/basket` | `store_id`, `period`, `min_support`, `min_confidence` | Market basket analysis — finds products frequently bought together (mlxtend) |
| `GET` | `/products/inventory` | `store_id`, `period`, `service_level` | Inventory optimization: EOQ, safety stock, reorder points |
| `GET` | `/products/stock-forecast` | `store_id`, `period` | Forecasts when each product will run out of stock |
| `GET` | `/products/stockout-impact` | `store_id`, `period` | Detects stockouts and estimates lost revenue |

---

## Marketing (6 endpoints)

Ad spend analytics and campaign performance.

| Method | Path | Params | Description |
|---|---|---|---|
| `GET` | `/marketing/summary` | `store_id`, `period` | Marketing KPIs: total spend, ROAS, CPC, CTR, conversion rate, CPA |
| `GET` | `/marketing/channels` | `store_id`, `period` | Per-channel breakdown (Google, Meta, TikTok, etc.) |
| `GET` | `/marketing/trends` | `store_id`, `period`, `granularity`, `metric` | Ad spend metrics over time |
| `GET` | `/marketing/campaigns` | `store_id`, `period`, `sort_by`, `limit` | Campaign ranking by chosen metric |
| `GET` | `/marketing/wasted-spend` | `store_id`, `period` | Campaigns spending on out-of-stock products |
| `GET` | `/marketing/category-roi` | `store_id`, `period` | Ad spend vs order revenue by product category |

---

## Insights (13 endpoints)

The intelligence engine — anomalies, root causes, health scoring, and SHAP explanations.

| Method | Path | Params | Description |
|---|---|---|---|
| `GET` | `/insights/summary` | `store_id`, `period` | Summary counts of insights, anomalies, and recommended actions |
| `GET` | `/insights` | `store_id`, `period` | Generate prioritized AI insights from all data sources |
| `GET` | `/insights/anomalies` | `store_id`, `period` | Detect anomalies across all metrics using IQR/Z-score |
| `GET` | `/insights/actions` | `store_id`, `period` | 6 data-driven actions with estimated dollar impact |
| `GET` | `/insights/drivers` | `store_id`, `period`, `metric` | Decompose metric change into causal factors (volume, price, mix, refunds, etc.) |
| `GET` | `/insights/missed-revenue` | `store_id`, `period` | Missed revenue detection: refund losses, churn losses, stockout signals |
| `GET` | `/insights/feed` | `store_id`, `period` | Unified, priority-sorted insight feed aggregating all sources |
| `GET` | `/insights/health-score` | `store_id`, `period` | Business health score (0-100): revenue growth 35%, customer health 25%, ops efficiency 20%, growth momentum 20% |
| `GET` | `/insights/explain` | `store_id`, `metric`, `period` | Plain-language explanation of a metric's current state |
| `GET` | `/insights/business-dna` | `store_id`, `period` | 6-dimension business fingerprint (radar chart data) with archetype |
| `GET` | `/insights/root-cause` | `store_id`, `period` | Ollama-powered root cause narrative for anomalies |
| `GET` | `/insights/shap` | `store_id`, `period` | SHAP feature importance for churn drivers |
| `POST` | `/insights/scenario` | `store_id`, `period`, `adjustments` (body) | What-If scenario simulator — adjust variables and see projected impact |

---

## Forecasting (2 endpoints)

Time-series forecasting using Prophet with linear regression fallback.

| Method | Path | Params | Description |
|---|---|---|---|
| `GET` | `/forecasting` | `store_id`, `metric`, `horizon_days` | Generate forecast for a metric (revenue, orders, customers). Returns historical data, forecasted values, and upper/lower confidence bounds. |
| `GET` | `/forecasting/metrics` | `store_id`, `horizon_days` | Quick forecast overview for all supported metrics at once |

---

## Sentiment (7 endpoints)

Review analysis and sentiment tracking.

| Method | Path | Params | Description |
|---|---|---|---|
| `GET` | `/sentiment/summary` | `store_id`, `period` | Sentiment KPIs: avg rating, sentiment score, review count with period comparison |
| `GET` | `/sentiment/ratings` | `store_id`, `period` | Star rating distribution (1-5) with sentiment scores per tier |
| `GET` | `/sentiment/trend` | `store_id`, `period` | Daily average sentiment trend over time |
| `GET` | `/sentiment/reviews` | `store_id`, `period`, `limit` | Recent reviews with sentiment labels (positive/neutral/negative) |
| `GET` | `/sentiment/products` | `store_id`, `period` | Products with lowest sentiment — need attention |
| `GET` | `/sentiment/keywords` | `store_id`, `period` | Top positive and negative keywords from reviews |
| `POST` | `/sentiment/analyze` | `store_id`, `limit` | Process unscored reviews and assign sentiment labels |

---

## Copilot (13 endpoints)

AI chat interface with Ollama model management.

| Method | Path | Description |
|---|---|---|
| `POST` | `/copilot/ask` | Send a question, receive AI-generated answer with RAG context |
| `GET` | `/copilot/suggestions` | Get list of suggested follow-up questions |
| `GET` | `/copilot/starters` | Get categorized conversation starters for the welcome screen |
| `POST` | `/copilot/warmup` | Pre-load active model into GPU/RAM |
| `GET` | `/copilot/status` | Check if Ollama is running and responsive |
| `GET` | `/copilot/models` | List all available models with install status and size |
| `GET` | `/copilot/models/recommendations` | Get model recommendations based on system specs |
| `GET` | `/copilot/models/active` | Get the currently active model name |
| `PUT` | `/copilot/models/active` | Switch to a different model |
| `POST` | `/copilot/models/install` | Download and install a model via Ollama |
| `DELETE` | `/copilot/models/{model_id}` | Delete an installed model |
| `POST` | `/copilot/feedback` | Submit thumbs up/down feedback on an answer |
| `GET` | `/copilot/feedback/stats/{store_id}` | Get feedback statistics for a store |

---

## Data Ingestion (19+ endpoints)

Multi-step data import pipeline.

| Method | Path | Description |
|---|---|---|
| `POST` | `/ingestion/upload-file` | Upload a single file (CSV/TSV/Excel), auto-detect schema, return preview |
| `POST` | `/ingestion/upload-files` | Upload multiple files at once with schema detection |
| `POST` | `/ingestion/confirm-import` | Run the full pipeline: map columns → clean → quality check → merge into DuckDB |
| `POST` | `/ingestion/confirm-batch-import` | Process multiple file imports in sequence |
| `POST` | `/ingestion/confirm-mixed-import` | Import a file that contains mixed data types (splits by type) |
| `DELETE` | `/ingestion/cancel-file` | Cancel/remove an uploaded file before import |
| `POST` | `/ingestion/load-sample` | Load the built-in demo dataset (~5,000 orders, 1,200 customers, etc.) |
| `POST` | `/ingestion/import-google-sheet` | Import from a public Google Sheets URL |
| `POST` | `/ingestion/import-google-sheets-batch` | Import multiple sheets from one spreadsheet |
| `GET` | `/ingestion/imports` | List all imports for a store |
| `GET` | `/ingestion/imports/{import_id}` | Get details of a specific import |
| `GET` | `/ingestion/imports/{import_id}/lineage` | Get the transformation lineage (steps) of an import |
| `GET` | `/ingestion/store-summary` | Data summary across all tables for a store |
| `GET` | `/ingestion/data-profile` | Column-level profiling: types, nulls, unique counts, distributions |
| `GET` | `/ingestion/check-duplicate` | Check if a file was already imported (by file hash) |
| `GET` | `/ingestion/template/{data_type}` | Download a template CSV for a specific data type |
| `GET` | `/ingestion/schema-reference/{data_type}` | Get the expected schema for a data type |
| `GET` | `/ingestion/schema-reference` | Get schemas for all data types |
| `GET` | `/ingestion/platform-guides` | Get platform-specific export guides (Shopify, Amazon, etc.) |
| `POST` | `/ingestion/validate` | Dry-run validation without importing |

---

## Connectors (7 endpoints)

External data source integration (Shopify, databases).

| Method | Path | Description |
|---|---|---|
| `POST` | `/connectors/sync` | Trigger immediate sync for a store's connector |
| `GET` | `/connectors/status/{store_id}` | Get sync status and next scheduled sync |
| `POST` | `/connectors/test-connection` | Test connector credentials without saving |
| `GET` | `/connectors/available-data/{store_id}` | List data types available from the connector |
| `GET` | `/connectors/{store_id}/tables` | List tables from a database connector |
| `POST` | `/connectors/{store_id}/preview-query` | Preview SQL query results |
| `POST` | `/connectors/{store_id}/import-tables` | Import multiple tables mapped to data types |

---

## Credentials (4 endpoints)

Encrypted credential storage for connectors.

| Method | Path | Description |
|---|---|---|
| `POST` | `/credentials` | Save or update an encrypted credential |
| `GET` | `/credentials/{store_id}` | List all credentials for a store (values masked) |
| `DELETE` | `/credentials/{credential_id}` | Delete a credential |
| `POST` | `/credentials/{credential_id}/test` | Test credential with a live connection check |

---

## Webhooks (4 endpoints)

Real-time data ingestion via webhooks (Shopify HMAC-verified).

| Method | Path | Description |
|---|---|---|
| `POST` | `/webhooks/shopify/{store_id}` | Receive and process a Shopify webhook payload |
| `GET` | `/webhooks/status/{store_id}` | Get webhook configuration and recent events |
| `POST` | `/webhooks/test/{store_id}` | Send a mock webhook through the pipeline |
| `POST` | `/webhooks/configure/{store_id}` | Generate webhook secret and return the URL |

---

## Sync Schedules (5 endpoints)

Recurring data sync management via APScheduler.

| Method | Path | Description |
|---|---|---|
| `POST` | `/sync/schedule` | Create or update a sync schedule |
| `GET` | `/sync/schedules/{store_id}` | List all sync schedules for a store |
| `DELETE` | `/sync/schedule/{schedule_id}` | Delete a sync schedule |
| `POST` | `/sync/trigger/{store_id}` | Trigger a manual sync using saved configuration |
| `GET` | `/sync/history/{store_id}` | Get recent sync history |

---

## Alerts (7 endpoints)

Alert and notification management.

| Method | Path | Description |
|---|---|---|
| `GET` | `/alerts` | List alerts with pagination and read/unread filter |
| `GET` | `/alerts/unread-count` | Get count of unread alerts |
| `POST` | `/alerts` | Create a new alert |
| `POST` | `/alerts/mark-read` | Mark specific alerts as read |
| `POST` | `/alerts/mark-all-read` | Mark all alerts as read for a store |
| `DELETE` | `/alerts/{alert_id}` | Delete an alert |
| `POST` | `/alerts/check-thresholds` | Run KPI threshold checks and generate alerts automatically |

---

## Export & Reports (4 endpoints)

Data export and report generation.

| Method | Path | Description |
|---|---|---|
| `GET` | `/export/preview` | Get row count before exporting |
| `POST` | `/export/csv` | Export data as a downloadable CSV file |
| `GET` | `/export/report` | Generate a summary report with key KPIs |
| `POST` | `/export/narrative-report` | Generate a full BI narrative report as PDF |

---

## Email (5 endpoints)

SMTP email configuration and digest sending.

| Method | Path | Description |
|---|---|---|
| `GET` | `/email/config` | Get current SMTP configuration (password masked) |
| `POST` | `/email/config` | Save SMTP configuration |
| `POST` | `/email/test` | Test SMTP connection |
| `POST` | `/email/send-digest` | Send an anomaly digest email |
| `GET` | `/email/history` | Get recent email send history |

---

## Data Viewer (5 endpoints)

Browse and manage raw analytical data.

| Method | Path | Description |
|---|---|---|
| `GET` | `/data-viewer/browse` | Browse DuckDB table with pagination, sorting, and search |
| `GET` | `/data-viewer/tables` | List all tables with row counts |
| `GET` | `/data-viewer/columns` | Get column metadata and quick stats for a table |
| `DELETE` | `/data-viewer/table-data` | Delete all rows for a specific table and store |
| `DELETE` | `/data-viewer/all-data` | Delete all analytical data for a store |

---

## Settings (6 endpoints)

User preferences and system configuration.

| Method | Path | Description |
|---|---|---|
| `GET` | `/settings/preferences` | Get all user settings as key-value pairs |
| `PUT` | `/settings/preferences` | Update settings (whitelisted keys only) |
| `GET` | `/settings/system-info` | Get storage usage, file sizes, and paths |
| `DELETE` | `/settings/cache` | Clear all cache files |
| `GET` | `/settings/exchange-rates` | Get current exchange rates for all supported currencies |
| `GET` | `/settings/exchange-rate/{currency}` | Get exchange rate for a single currency |

---

## Stores (10 endpoints)

Store and user profile management.

| Method | Path | Description |
|---|---|---|
| `GET` | `/stores/profile` | Get the user profile |
| `PATCH` | `/stores/profile` | Update profile fields |
| `GET` | `/stores` | List all stores |
| `POST` | `/stores` | Create a new store |
| `GET` | `/stores/{store_id}` | Get store details |
| `PATCH` | `/stores/{store_id}` | Update store settings |
| `POST` | `/stores/{store_id}/deactivate` | Soft-delete (deactivate) a store |
| `POST` | `/stores/{store_id}/reactivate` | Reactivate a deactivated store |
| `DELETE` | `/stores/{store_id}` | Permanently delete store and all its data |
| `GET` | `/stores/{store_id}/data-counts` | Get row counts across all tables for a store |

---

## System (3 endpoints)

System-level operations.

| Method | Path | Description |
|---|---|---|
| `GET` | `/system/info` | System info: Python version, platform, DuckDB/SQLite versions, memory, store count |
| `GET` | `/system/tasks/{store_id}` | Get background task history for a store |
| `POST` | `/system/shutdown` | Graceful engine shutdown (used by Tauri on app close) |

---

## Endpoint Count Summary

| Router | Endpoints |
|---|---|
| Health | 1 |
| Auth | 11 |
| Dashboard | 5 |
| Customers | 7 |
| Products | 9 |
| Marketing | 6 |
| Insights | 13 |
| Forecasting | 2 |
| Sentiment | 7 |
| Copilot | 13 |
| Ingestion | 19+ |
| Connectors | 7 |
| Credentials | 4 |
| Webhooks | 4 |
| Sync | 5 |
| Alerts | 7 |
| Export | 4 |
| Email | 5 |
| Data Viewer | 5 |
| Settings | 6 |
| Stores | 10 |
| System | 3 |
| **Total** | **~150+** |
