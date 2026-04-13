# Engine Guide

This document covers the Python backend — how it's structured, what each service does, how the data pipeline works, and how the ML models operate.

---

## Stack

| Technology | Version | Role |
|---|---|---|
| FastAPI | 0.115 | Web framework |
| Uvicorn | 0.34 | ASGI server |
| DuckDB | 1.2 | Analytical query engine |
| SQLite | (built-in) | Metadata storage |
| Pandas | 2.2 | Data manipulation |
| NumPy | 2.2 | Numerical computing |
| scikit-learn | 1.6 | ML models (clustering, classification) |
| Prophet | 1.1 | Time-series forecasting |
| lifetimes | 0.11 | Customer lifetime value / churn (BG/NBD model) |
| mlxtend | 0.23 | Association rule mining (basket analysis) |
| SHAP | 0.47 | Feature importance explanations |
| TextBlob | 0.18 | Sentiment analysis |
| scipy | 1.17 | Statistical tests (Welch t-test, Z-score) |
| httpx | 0.28 | Async HTTP client (for Ollama, exchange rates) |
| bcrypt | 4.3 | Password hashing |
| cryptography | 44.0 | Fernet encryption for stored credentials |
| APScheduler | 3.11 | Recurring sync job scheduler |
| reportlab | 4.4 | PDF report generation |
| Ollama | 0.6 | Local LLM client for AI Copilot |

---

## Directory Structure

```
engine/app/
├── main.py              # FastAPI app setup, router registration, lifespan
├── config.py            # Environment variables and path configuration
├── api/                 # 22 API router files
│   ├── router_alerts.py
│   ├── router_auth.py
│   ├── router_connectors.py
│   ├── router_copilot.py
│   ├── router_credentials.py
│   ├── router_customers.py
│   ├── router_dashboard.py
│   ├── router_data_viewer.py
│   ├── router_email.py
│   ├── router_export.py
│   ├── router_forecasting.py
│   ├── router_health.py
│   ├── router_ingestion.py
│   ├── router_insights.py
│   ├── router_marketing.py
│   ├── router_products.py
│   ├── router_sentiment.py
│   ├── router_settings.py
│   ├── router_stores.py
│   ├── router_sync.py
│   ├── router_system.py
│   └── router_webhooks.py
├── core/                # Infrastructure
│   ├── database.py      # DuckDB + SQLite connections and schema init
│   ├── encryption.py    # Fernet JSON encrypt/decrypt
│   ├── logging_config.py # Rotating file logger
│   ├── middleware.py     # Auth, request logging, request ID middleware
│   ├── scheduler.py     # APScheduler singleton
│   └── task_manager.py  # Background task tracking
├── models/              # Pydantic data models
│   ├── alerts.py
│   ├── common.py
│   ├── credentials.py
│   ├── enums.py
│   ├── export.py
│   ├── ingestion.py
│   ├── stores.py
│   └── system.py
└── services/            # Business logic (14 modules)
    ├── alerts/          # Alert management + email sending
    ├── connectors/      # Shopify, Google Sheets, Database connectors
    ├── copilot/         # AI chat, RAG context, feedback, spell correction
    ├── currency/        # Exchange rate service (ECB data)
    ├── customers/       # Customer analytics, churn, cohort, stories
    ├── dashboard/       # KPIs, time-series, revenue at risk
    ├── export/          # CSV, narrative report, PDF generation
    ├── forecasting/     # Prophet forecasting
    ├── ingestion/       # File parsing, cleaning, mapping, merging
    ├── insights/        # Anomaly detection, causal analysis, health score
    ├── marketing/       # Ad spend analytics, channel analysis
    ├── products/        # Product analytics, basket analysis, inventory
    ├── quality/         # Data quality scoring
    ├── sentiment/       # Review sentiment analysis
    ├── stores/          # Store CRUD
    ├── sync/            # Sync orchestration
    └── webhooks/        # Shopify webhook handling
```

---

## Application Startup

When the engine starts (`main.py` lifespan), it:

1. **Initializes DuckDB schema** — Creates all 6 analytical tables if they don't exist
2. **Initializes SQLite schema** — Creates all metadata tables, runs migrations
3. **Runs integrity checks** — Verifies database files are not corrupted
4. **Seeds system_meta** — Sets `schema_version=1`, `first_run_completed=false` if first run
5. **Starts APScheduler** — Restores any persisted sync schedules
6. **Starts Ollama health poller** — Background daemon thread checks Ollama every 60 seconds
7. **Cleans recycle bin** — Purges datasets deleted more than 30 days ago

---

## Core Infrastructure

### Database (database.py)

Two database connections with thread-safe access:

**DuckDB** (analytical data):
- Single shared connection (singleton)
- Each API request gets its own `cursor()` — this prevents "no open result set" errors when the frontend fires parallel requests
- All queries use parameterized statements

**SQLite** (metadata):
- Per-thread connections via `threading.local()`
- WAL mode enabled for concurrent readers
- `row_factory` set for dict-like row access
- Each thread gets its own connection to prevent "bad parameter or API misuse" errors

### Middleware Stack

Three middlewares applied to every request (in order):

1. **RequestIdMiddleware** — Generates a UUID4 and attaches it as the `X-Request-Id` header. Useful for tracing.
2. **RequestLoggingMiddleware** — Logs HTTP method, path, status code, and response time for every request.
3. **AuthMiddleware** — Validates the session token. Skips `/health`, `/auth/*`, and `/webhooks/*` paths.

### Encryption (encryption.py)

Uses Fernet symmetric encryption for storing sensitive data (API keys, database passwords):

- `encrypt_json(data: dict) → str` — Encrypts a dictionary to a base64 string
- `decrypt_json(encrypted: str) → dict` — Decrypts back to a dictionary
- Encryption key is auto-generated on first use, stored in `data/encryption.key` with `0o600` permissions
- Used by: credential storage, email config, API key storage

### Scheduler (scheduler.py)

APScheduler singleton for recurring data syncs:

- Job store: SQLite (persisted across restarts)
- Jobs are created via `/sync/schedule` API
- On engine restart, all schedules are restored automatically
- Each job triggers `sync_runner.run_sync()` which calls the appropriate connector

---

## Service Modules

### Ingestion (`services/ingestion/`)

The data import pipeline. This is the most complex subsystem. Here's what each file does:

| File | Purpose |
|---|---|
| `file_parser.py` | Parses CSV, TSV, TXT, and Excel files. Auto-detects delimiter, encoding, and header row. 500 MB file size limit. |
| `schema_detector.py` | Looks at column names and data types to detect what kind of data this is (orders? customers? products?). Uses pattern matching against canonical column names. |
| `column_mapper.py` | Maps uploaded column names to the canonical schema. Three-tier matching: exact match → synonym match (350+ platform-specific synonyms) → fuzzy match (Levenshtein distance ≤ 2). |
| `data_cleaner.py` | Strips whitespace, removes empty rows, normalizes nulls, parses dates, cleans numeric columns, normalizes currency values, normalizes order status. |
| `pii_masker.py` | SHA-256 hashes email and name columns into `email_hash` and `name_hash`. Applied automatically unless the user disables PII masking. |
| `channel_normalizer.py` | Normalizes ad channel names: "Google Ads" → "google", "Facebook Ads" → "meta", adds Shopify/WooCommerce channels. |
| `quality_checker.py` | Runs 8 weighted quality checks and produces a 0-100 score. |
| `merge_engine.py` | Merges cleaned data into DuckDB using UPSERT (match on natural keys like order_id), APPEND, or REPLACE strategies. |
| `google_sheets.py` | Extracts CSV export URL from public Google Sheets URLs, downloads, and parses. |
| `sample_data.py` | Generates synthetic demo data: ~5,000 orders, 1,200 customers, 150 products, 800 reviews with realistic e-commerce patterns. |
| `template_service.py` | Provides downloadable CSV templates for each data type. |

### Import Pipeline Flow

```
1. Upload file
   → file_parser.py: parse to DataFrame
   → schema_detector.py: detect data type + confidence
   → column_mapper.py: suggest column mappings
   → Return preview (10 sample rows)

2. User confirms (with optional mapping edits)
   → column_mapper.py: apply final mappings
   → data_cleaner.py: clean and normalize
   → channel_normalizer.py: standardize ad channels (if ad_spend)
   → pii_masker.py: hash PII columns
   → quality_checker.py: score quality
   → merge_engine.py: UPSERT into DuckDB
   → Save import history + lineage steps to SQLite
```

### Dashboard (`services/dashboard/`)

| File | What It Calculates |
|---|---|
| `kpi_calculator.py` | 10 KPIs: revenue, order count, unique customers, AOV, repeat rate, new vs returning, refund rate, avg items per order, revenue per customer, churn proxy. Each with current value and period-over-period change. |
| `time_series.py` | Generates time-series data points for any metric at day/week/month granularity. |
| `revenue_at_risk.py` | Identifies customers overdue for a purchase (based on their average order frequency) and sums their expected spend. This is the "revenue at risk" dollar clock. |

### Customers (`services/customers/`)

| File | What It Does |
|---|---|
| `customer_analytics.py` | Core customer metrics: summary stats, top customers by spend, spend-tier segmentation (VIP/Regular/Low-value), customer growth over time. |
| `churn_predictor.py` | Uses the BG/NBD model from the `lifetimes` library to predict churn probability for each customer. Requires frequency, recency, and T (customer age) inputs. |
| `cohort_replay.py` | Builds a retention heatmap: groups customers by their first-purchase month, then tracks how many return in subsequent months. |
| `customer_story.py` | Generates a plain-language narrative about a specific customer's journey: when they started, how often they buy, what they buy, their value tier. |

### Products (`services/products/`)

| File | What It Does |
|---|---|
| `product_analytics.py` | Core product metrics: summary stats, top products, category breakdown, revenue trend. |
| `basket_analysis.py` | Market basket analysis using `mlxtend`. Finds frequently co-purchased product pairs with support, confidence, and lift metrics. |
| `lifecycle_classifier.py` | BCG-inspired 4-quadrant classification: **Rising Star** (growing revenue + volume), **Cash Cow** (stable high revenue), **Fading** (declining revenue), **Dead Weight** (low and declining). |
| `inventory_optimizer.py` | Calculates Economic Order Quantity (EOQ), safety stock, and reorder points based on demand rate and lead times. |
| `stock_forecast.py` | Projects when each product will run out of stock based on current inventory and daily demand rate. |
| `stockout_analyzer.py` | Detects periods when a product had zero stock and estimates revenue lost during those periods. |

### Marketing (`services/marketing/`)

| File | What It Does |
|---|---|
| `marketing_kpi.py` | Core marketing metrics: total ad spend, ROAS, CPC, CTR, conversion rate, CPA. |
| `channel_analyzer.py` | Per-channel breakdown of all marketing metrics. |
| `campaign_ranker.py` | Ranks campaigns by chosen metric (ROAS, spend, conversions). |
| `ad_stock_correlation.py` | Detects campaigns spending on products that are out of stock (wasted spend). Calculates category-level ROI. |

### Insights (`services/insights/`)

The intelligence layer — the most feature-rich service module.

| File | What It Does |
|---|---|
| `insight_engine.py` | Generates prioritized AI insights from all data. 15 rules (R001-R015) including high-LTV churn cross-join, segment imbalance, demand surge, complaint clusters, 3σ revenue anomalies. Includes confidence scoring. |
| `anomaly_detection.py` | Rolling IQR-based anomaly detection across all KPIs. Stores detected anomalies in SQLite with timestamps and detection time. |
| `causal_engine.py` | Decomposes revenue changes into components: volume effect, price effect, interaction effect, refund impact, channel mix shift, category mix shift, new vs returning customer shift. |
| `explain_metric.py` | Generates a plain-English explanation of why a metric is at its current level. |
| `health_score.py` | Composite business health score (0-100): revenue growth trend (35%), customer health (25%), operational efficiency (20%), growth momentum (20%). |
| `missed_revenue.py` | Detects three types of missed revenue: refund losses, churn losses (customers who stopped buying), stockout signal losses. |
| `feed_service.py` | Aggregates insights, anomalies, and actions into a single unified, priority-sorted feed. |
| `business_dna.py` | Creates a 6-dimension "fingerprint" of the business (pricing power, customer loyalty, product diversity, marketing efficiency, operational health, growth trajectory) and assigns an archetype. |
| `root_cause_narrator.py` | Uses Ollama to generate human-readable root cause narratives for detected anomalies. Falls back to template-based narratives if Ollama is offline. |
| `scenario_simulator.py` | What-If simulator: user adjusts variables (e.g., +10% marketing spend, -5% refund rate) and sees projected impact on revenue. |
| `shap_explainer.py` | Uses SHAP to explain which features most strongly drive customer churn. |

### Forecasting (`services/forecasting/`)

| File | What It Does |
|---|---|
| `forecast_service.py` | Time-series forecasting. Uses Facebook Prophet if available, falls back to linear regression. Returns historical data, forecasted values, and upper/lower confidence bounds for 30-90 day horizons. |

### Sentiment (`services/sentiment/`)

| File | What It Does |
|---|---|
| `sentiment_service.py` | Analyzes product reviews. Uses TextBlob for polarity scoring. Extracts top positive/negative keywords. Calculates per-product sentiment scores. Generates rating distribution and trend data. |

### Copilot (`services/copilot/`)

The AI chat system. This is a sophisticated multi-layer system:

| File | What It Does |
|---|---|
| `copilot_service.py` | Main service. RAG context builder pulls store data before each query. Routes questions to Ollama (if available) or rule-based patterns (11 SQL templates). Manages model lifecycle (list, install, delete, switch). Rate limited: 30/min, 500 word max. |
| `feedback_service.py` | Stores thumbs up/down feedback on AI answers. Tracks satisfaction metrics per store. |
| `context_cache.py` | Caches frequently-used RAG context to avoid repeated DB queries. |
| `spell_corrector.py` | Basic spell correction for user queries before processing. |

**RAG Context**: Before sending a question to Ollama, the service builds a rich context block containing:
- Store overview (name, platform, industry)
- Monthly revenue and order trends
- Customer count and returning rate
- Top products and categories
- Refund rates
- Review sentiment summary
- Active anomalies
- Health score

This context is injected as the system prompt, so the LLM answers with knowledge of the user's actual business data.

### Connectors (`services/connectors/`)

External data source integrations:

| File | What It Does |
|---|---|
| `base.py` | Abstract base class for all connectors. Defines `sync()`, `test_connection()`, `get_available_data()`. |
| `shopify_connector.py` | Shopify REST API: cursor-based pagination, 2 req/s rate limit. Syncs orders, customers, products, reviews, stock. |
| `google_sheets_connector.py` | Google Sheets API v4: reads public sheets by URL. |
| `database_connector.py` | PostgreSQL and MySQL connector. Supports structured table mapping and custom SQL queries. Read-only enforcement (SELECT/WITH/EXPLAIN/SHOW only). |
| `field_maps.py` | Maps connector-specific field names to NOVEM's canonical schema. |

### Export (`services/export/`)

| File | What It Does |
|---|---|
| `export_service.py` | Exports DuckDB table data as CSV files. Auto-cleans files older than 1 hour. |
| `report_builder.py` | Builds narrative summary reports with KPI highlights and trend descriptions. |
| `pdf_generator.py` | Generates PDF reports using ReportLab. |

### Currency (`services/currency/`)

| File | What It Does |
|---|---|
| `exchange_service.py` | Fetches live exchange rates from frankfurter.app (ECB data, free, no API key). 1-hour cache with fallback static rates for 24 currencies. |

### Alerts (`services/alerts/`)

| File | What It Does |
|---|---|
| `alert_service.py` | CRUD for alerts. Threshold checking against KPIs. |
| `email_service.py` | SMTP email sending for anomaly digests and verification codes. Uses encrypted credentials from Fernet. |

---

## Configuration

`engine/app/config.py` manages all environment variables:

| Variable | Default | Description |
|---|---|---|
| `ENGINE_PORT` | `44945` | HTTP port |
| `DATA_DIR` | `./data/` | Database file storage |
| `CONFIG_DIR` | `./config/` | Configuration files |
| `LOG_LEVEL` | `info` | Logging level |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama LLM server URL |
| `DUCKDB_PATH` | `data/analytics.duckdb` | DuckDB file path |
| `SQLITE_PATH` | `data/metadata.sqlite` | SQLite file path |
| `CORS_ORIGINS` | `localhost:1420,5173,tauri://` | Allowed CORS origins |

In production (PyInstaller), paths resolve relative to the executable. Environment variables `NOVEM_DATA_DIR`, `NOVEM_CONFIG_DIR`, and `NOVEM_ENGINE_DIR` override defaults.

---

## Logging

Configured in `core/logging_config.py`:

- **File**: Rotating file handler, 10 MB max per file, 3 backup files
- **Location**: `data/engine.log`
- **Format**: `[timestamp] [level] [module] message`
- **Levels**: INFO for request handling, WARNING for recoverable errors, ERROR for failures
- **Request tracing**: Every request gets a UUID in the `X-Request-Id` header for correlation

---

## Error Handling Pattern

All API endpoints follow a consistent error pattern:

```python
@router.get("/kpis")
async def dashboard_kpis(store_id: str, period: str = "30d"):
    try:
        data = kpi_calculator.get_kpis(store_id, period)
        return {"success": True, "data": data, "error": None}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to calculate KPIs: {e}")
        raise HTTPException(status_code=500, detail="Failed to calculate KPIs")
```

Rules:
- Never return raw Python tracebacks to the frontend
- Use appropriate HTTP status codes (400, 404, 422, 500)
- Log the full error server-side, return a clean message to the client
- ML model failures (insufficient data, convergence) return specific error codes so the frontend can show guidance

---

## Adding a New Service

1. Create the service file in `engine/app/services/<module>/your_service.py`
2. Write pure functions that take `store_id` and other params, query DuckDB/SQLite, return typed results
3. Create or edit the router in `engine/app/api/router_<module>.py`
4. Register the router in `engine/app/main.py` (if new)
5. Add Pydantic models in `engine/app/models/` if needed
6. Use parameterized queries for all database access
7. Log with the `logging` module, not `print()`
