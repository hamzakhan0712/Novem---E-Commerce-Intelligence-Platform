# Data Model

This document describes every database table in NOVEM — what it stores, how it's structured, and how the tables relate to each other.

NOVEM uses **two separate databases** for two different purposes:

- **DuckDB** (`analytics.duckdb`) — All analytical/business data. Optimized for fast aggregations and scans.
- **SQLite** (`metadata.sqlite`) — User settings, session management, import history, and configuration. Optimized for small transactional workloads.

---

## DuckDB — Analytical Tables

All analytical tables are scoped by `store_id`. This provides complete data isolation between stores. A user with multiple stores (e.g., Shopify + Amazon) has fully separate datasets.

### orders

The core table. Every row is a single line item in an order.

| Column | Type | Description |
|---|---|---|
| `store_id` | VARCHAR | Store this order belongs to (FK logical) |
| `order_id` | VARCHAR | Order identifier |
| `order_date` | TIMESTAMP | When the order was placed |
| `customer_id` | VARCHAR | Customer identifier |
| `customer_email_hash` | VARCHAR | SHA-256 hash of customer email (PII masked) |
| `customer_name_hash` | VARCHAR | SHA-256 hash of customer name (PII masked) |
| `product_id` | VARCHAR | Product purchased |
| `product_name` | VARCHAR | Product name (denormalized for query speed) |
| `category` | VARCHAR | Product category |
| `quantity` | DECIMAL(12,2) | Units purchased |
| `unit_price` | DECIMAL(12,2) | Price per unit |
| `total_price` | DECIMAL(12,2) | Line item total (quantity × unit_price) |
| `discount_amount` | DECIMAL(12,2) | Discount applied to this line |
| `currency` | VARCHAR(10) | Currency code (default: INR) |
| `status` | VARCHAR | Order status: completed, pending, refunded, cancelled |
| `refund_amount` | DECIMAL(12,2) | Amount refunded (if any) |
| `refund_reason` | VARCHAR | Reason for refund |
| `channel` | VARCHAR | Sales channel (website, shopify, amazon, etc.) |
| `region` | VARCHAR | Customer region/location |
| `line_item_index` | INTEGER | Line item position within order (0-based) |
| `created_at` | TIMESTAMP | Record creation time |
| `updated_at` | TIMESTAMP | Last update time |

**Primary Key**: `(store_id, order_id, product_id, line_item_index)`

**Revenue calculation**: Net revenue = `SUM(total_price - discount_amount)`. This is used consistently across all analytics.

---

### customers

Aggregated customer profile. Updated on each import.

| Column | Type | Description |
|---|---|---|
| `store_id` | VARCHAR | Store this customer belongs to |
| `customer_id` | VARCHAR | Customer identifier |
| `email_hash` | VARCHAR | SHA-256 hash of email |
| `name_hash` | VARCHAR | SHA-256 hash of name |
| `first_order_date` | TIMESTAMP | Date of first purchase |
| `last_order_date` | TIMESTAMP | Date of most recent purchase |
| `total_orders` | INTEGER | Lifetime order count |
| `total_spend` | DECIMAL(12,2) | Lifetime spend total |
| `avg_order_value` | DECIMAL(12,2) | Average order value |
| `region` | VARCHAR | Customer region |
| `created_at` | TIMESTAMP | Record creation time |
| `updated_at` | TIMESTAMP | Last update time |

**Primary Key**: `(store_id, customer_id)`

---

### products

Product catalog. Each row is a unique product.

| Column | Type | Description |
|---|---|---|
| `store_id` | VARCHAR | Store this product belongs to |
| `product_id` | VARCHAR | Product identifier |
| `product_name` | VARCHAR | Display name |
| `category` | VARCHAR | Product category |
| `subcategory` | VARCHAR | Product subcategory |
| `parent_product_id` | VARCHAR | Parent product (for variants) |
| `unit_cost` | DECIMAL(12,2) | Cost per unit (for margin calculation) |
| `current_stock` | INTEGER | Current inventory level |
| `status` | VARCHAR | active, discontinued |
| `size` | VARCHAR | Size variant |
| `color` | VARCHAR | Color variant |
| `created_at` | TIMESTAMP | Record creation time |
| `updated_at` | TIMESTAMP | Last update time |

**Primary Key**: `(store_id, product_id)`

---

### ad_spend

Marketing spend data. One row per channel per campaign per day.

| Column | Type | Description |
|---|---|---|
| `store_id` | VARCHAR | Store this data belongs to |
| `date` | DATE | Spend date |
| `channel` | VARCHAR | Normalized channel name (google, meta, tiktok, email, etc.) |
| `campaign_name` | VARCHAR | Campaign identifier |
| `impressions` | INTEGER | Ad impressions |
| `clicks` | INTEGER | Ad clicks |
| `spend` | DECIMAL(12,2) | Money spent |
| `currency` | VARCHAR(3) | Currency code |
| `conversions` | INTEGER | Conversion count |
| `revenue_attributed` | DECIMAL(12,2) | Revenue attributed to this campaign |
| `created_at` | TIMESTAMP | Record creation time |
| `updated_at` | TIMESTAMP | Last update time |

**Primary Key**: `(store_id, date, channel, campaign_name)`

**Channel normalization**: During import, channel names are standardized: "Google Ads" → "google", "Facebook Ads" → "meta", "TikTok Ads" → "tiktok", etc.

---

### reviews

Product reviews with sentiment scores.

| Column | Type | Description |
|---|---|---|
| `store_id` | VARCHAR | Store this review belongs to |
| `review_id` | VARCHAR | Review identifier |
| `product_id` | VARCHAR | Product being reviewed |
| `customer_id` | VARCHAR | Customer who wrote the review |
| `review_date` | TIMESTAMP | When the review was posted |
| `rating` | INTEGER | Star rating (1-5) |
| `review_text` | TEXT | Full review text |
| `sentiment_score` | DECIMAL(4,3) | TextBlob polarity score (-1.0 to 1.0) |
| `sentiment_label` | VARCHAR | positive, neutral, negative |
| `aspects` | VARCHAR | Extracted aspect keywords (JSON string) |
| `created_at` | TIMESTAMP | Record creation time |
| `updated_at` | TIMESTAMP | Last update time |

**Primary Key**: `(store_id, review_id)`

**Sentiment scoring**: Sentiment is scored using TextBlob. Scores > 0.1 are labeled "positive", < -0.1 are "negative", everything else is "neutral".

---

### stock_levels

Inventory snapshots over time. One row per product per date per warehouse.

| Column | Type | Description |
|---|---|---|
| `store_id` | VARCHAR | Store this data belongs to |
| `product_id` | VARCHAR | Product identifier |
| `snapshot_date` | DATE | Date of inventory snapshot |
| `quantity_on_hand` | INTEGER | Units in stock |
| `lead_time_days` | INTEGER | Days to restock from supplier |
| `reorder_point` | INTEGER | Stock level that triggers reorder |
| `safety_stock` | INTEGER | Minimum safety buffer |
| `warehouse` | VARCHAR | Warehouse name/location |
| `location` | VARCHAR | Sub-location within warehouse |
| `status` | VARCHAR | in_stock, low, out_of_stock |
| `created_at` | TIMESTAMP | Record creation time |
| `updated_at` | TIMESTAMP | Last update time |

**Primary Key**: `(store_id, product_id, snapshot_date)`

---

## SQLite — Metadata Tables

These tables store configuration, authentication, and operational metadata. They are low-volume and transactional.

### user_profile

Single-user profile (one row per installation).

| Column | Type | Description |
|---|---|---|
| `id` | TEXT | Always 'default' (single user) |
| `name` | TEXT | User's display name |
| `avatar_seed` | TEXT | Seed for deterministic avatar generation |
| `avatar_photo` | TEXT | Base64 photo (optional) |
| `email` | TEXT | User's email address |
| `password_hash` | TEXT | bcrypt-hashed password |
| `is_setup_complete` | INTEGER | Whether first-time setup is done (0/1) |
| `currency` | TEXT | Default currency code |
| `region` | TEXT | Country/region code |
| `date_format` | TEXT | Date display format preference |
| `fiscal_year_start` | TEXT | Fiscal year start month |
| `timezone` | TEXT | Timezone string |
| `security_question` | TEXT | Forgot-password security question |
| `security_answer_hash` | TEXT | Hashed security answer |
| `email_verified` | INTEGER | Whether email is verified (0/1) |
| `created_at` | TEXT | Profile creation timestamp |
| `updated_at` | TEXT | Last update timestamp |

---

### sessions

Active authentication sessions. Cleared on engine restart (enforces password policy).

| Column | Type | Description |
|---|---|---|
| `token` | TEXT | Session token (secrets.token_urlsafe(32)) |
| `created_at` | TEXT | When the session was created |
| `expires_at` | TEXT | Expiration time (24 hours after creation) |

---

### stores

User's e-commerce stores. A user can have multiple stores.

| Column | Type | Description |
|---|---|---|
| `id` | TEXT | UUID primary key |
| `name` | TEXT | Store display name |
| `platform` | TEXT | shopify, woocommerce, amazon, other |
| `url` | TEXT | Store URL |
| `currency` | TEXT | Store's currency code |
| `timezone` | TEXT | Store's timezone |
| `industry` | TEXT | Industry template: general, fashion, electronics, etc. |
| `description` | TEXT | Store description |
| `is_active` | INTEGER | Active/deactivated flag |
| `created_at` | TEXT | Creation timestamp |
| `updated_at` | TEXT | Last update timestamp |

---

### import_history

Audit trail for every data import.

| Column | Type | Description |
|---|---|---|
| `id` | TEXT | UUID primary key |
| `store_id` | TEXT | FK → stores.id (CASCADE delete) |
| `data_type` | TEXT | orders, customers, products, ad_spend, reviews, stock_levels |
| `source_type` | TEXT | file, google_sheets, shopify_api, database, sample, etc. |
| `source_name` | TEXT | Original filename or source label |
| `source_path` | TEXT | File system path (temp storage) |
| `file_hash` | TEXT | SHA-256 hash of imported file (deduplication) |
| `row_count_raw` | INTEGER | Rows in the original file |
| `row_count_new` | INTEGER | New rows inserted |
| `row_count_updated` | INTEGER | Existing rows updated |
| `row_count_skipped` | INTEGER | Rows skipped (duplicates, errors) |
| `health_score` | INTEGER | Quality score (0-100) |
| `health_details` | TEXT | JSON array of quality check results |
| `schema_mapping` | TEXT | JSON array of column mappings used |
| `status` | TEXT | completed, failed, cancelled |
| `error_message` | TEXT | Error details (if failed) |
| `imported_at` | TEXT | Import timestamp |
| `duration_ms` | INTEGER | Processing time in milliseconds |

---

### import_lineage

Step-by-step transformation log for each import. Tracks what happened to the data at each pipeline stage.

| Column | Type | Description |
|---|---|---|
| `id` | TEXT | UUID primary key |
| `import_id` | TEXT | FK → import_history.id (CASCADE delete) |
| `step_order` | INTEGER | Order of this step (1, 2, 3, ...) |
| `description` | TEXT | What this step did ("Removed 3 empty rows") |
| `rows_before` | INTEGER | Row count before this step |
| `rows_after` | INTEGER | Row count after this step |
| `timestamp` | TEXT | When this step ran |

---

### alerts

System alerts and notifications.

| Column | Type | Description |
|---|---|---|
| `id` | TEXT | UUID primary key |
| `store_id` | TEXT | FK → stores.id |
| `module` | TEXT | Source module (dashboard, insights, ingestion, etc.) |
| `severity` | TEXT | info, warning, critical |
| `title` | TEXT | Alert headline |
| `message` | TEXT | Alert body text |
| `is_read` | INTEGER | Read/unread flag (0/1) |
| `created_at` | TEXT | Creation timestamp |

---

### settings

Key-value configuration store. Whitelisted keys only.

| Column | Type | Description |
|---|---|---|
| `key` | TEXT | Setting name (e.g., "theme", "currency", "industry_template") |
| `value` | TEXT | Setting value |

Common keys: `theme`, `currency`, `date_format`, `fiscal_year_start`, `password_policy`, `pii_masking_enabled`, `industry_template`, `active_ollama_model`.

---

### store_credentials

Encrypted credentials for external connectors.

| Column | Type | Description |
|---|---|---|
| `id` | TEXT | UUID primary key |
| `store_id` | TEXT | FK → stores.id (CASCADE delete) |
| `credential_type` | TEXT | shopify, woocommerce, google_sheets, postgresql, mysql, webhook |
| `credentials_encrypted` | TEXT | Fernet-encrypted JSON blob containing API keys, passwords, etc. |
| `created_at` | TEXT | Creation timestamp |
| `updated_at` | TEXT | Last update timestamp |

---

### webhook_log

Audit log for received webhooks.

| Column | Type | Description |
|---|---|---|
| `id` | TEXT | UUID primary key |
| `store_id` | TEXT | Store that received the webhook |
| `platform` | TEXT | shopify, woocommerce |
| `topic` | TEXT | Event type (orders/create, products/update, etc.) |
| `payload_hash` | TEXT | Hash of the payload (deduplication) |
| `status` | TEXT | received, processed, failed |
| `error` | TEXT | Error message (if failed) |
| `received_at` | TEXT | When the webhook arrived |

---

### sync_schedules

Recurring data sync schedules for connectors.

| Column | Type | Description |
|---|---|---|
| `id` | TEXT | UUID primary key |
| `store_id` | TEXT | FK → stores.id (CASCADE delete) |
| `connector_type` | TEXT | shopify, woocommerce, google_sheets, database |
| `data_types` | TEXT | JSON array of data types to sync |
| `interval_minutes` | INTEGER | Sync interval (default: 60) |
| `is_active` | INTEGER | Active/paused flag |
| `last_sync_at` | TEXT | Last sync timestamp |
| `last_sync_status` | TEXT | success, failed, partial |
| `created_at` | TEXT | Creation timestamp |
| `updated_at` | TEXT | Last update timestamp |

---

### background_tasks

Tracks long-running background operations.

| Column | Type | Description |
|---|---|---|
| `id` | TEXT | UUID primary key |
| `store_id` | TEXT | FK → stores.id |
| `task_type` | TEXT | sync, import, analysis, export |
| `status` | TEXT | pending, running, completed, failed |
| `progress` | INTEGER | Progress percentage (0-100) |
| `error` | TEXT | Error message (if failed) |
| `created_at` | TEXT | Creation timestamp |
| `updated_at` | TEXT | Last update timestamp |

---

### system_meta

System-level key-value metadata.

| Column | Type | Description |
|---|---|---|
| `key` | TEXT | Meta key |
| `value` | TEXT | Meta value |

Seeded values: `schema_version` (1), `first_run_completed` (false/true).

---

## Data Relationships

```
stores ──────┬──── import_history ──── import_lineage
             ├──── alerts
             ├──── store_credentials
             ├──── webhook_log
             ├──── sync_schedules
             ├──── background_tasks
             │
             └──── (DuckDB: orders, customers, products,
                    ad_spend, reviews, stock_levels)
                    ↑ all filtered by store_id

user_profile (singleton — one row only)
sessions (auth tokens — cleared on restart)
settings (key-value pairs)
system_meta (schema version, flags)
```

### Store Isolation

Every analytical query includes a `WHERE store_id = ?` clause. This means:
- Deleting a store cascades to all its metadata (import history, credentials, schedules)
- DuckDB data must be cleaned separately (the `DELETE FROM orders WHERE store_id = ?` pattern)
- Switching stores in the UI just changes which `store_id` is passed to API calls

### Import Deduplication

Files are deduplicated by `file_hash` (SHA-256 of file contents). If the same file is uploaded twice, the system detects it and asks the user to confirm re-import.

### Merge Strategy

When importing data, the merge engine uses **UPSERT** by default:
- **Orders**: Match on `(store_id, order_id, product_id, line_item_index)`
- **Customers**: Match on `(store_id, customer_id)`
- **Products**: Match on `(store_id, product_id)`
- **Ad Spend**: Match on `(store_id, date, channel, campaign_name)`
- **Reviews**: Match on `(store_id, review_id)`
- **Stock Levels**: Match on `(store_id, product_id, snapshot_date)`

If a matching row exists, it's updated. If not, it's inserted.
