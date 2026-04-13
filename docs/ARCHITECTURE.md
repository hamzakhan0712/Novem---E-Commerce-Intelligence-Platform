# Architecture

This document explains how NOVEM is structured, how the layers talk to each other, and why certain design decisions were made.

---

## High-Level Overview

NOVEM has three layers stacked together into a single desktop application:

```
┌──────────────────────────────────────────────────┐
│                  Tauri Shell (Rust)               │
│    Window management · Engine lifecycle · IPC     │
├──────────────────────────────────────────────────┤
│              Desktop Frontend (React)             │
│   Pages · Components · Hooks · Zustand Stores     │
├──────────────────────────────────────────────────┤
│            Compute Engine (FastAPI/Python)         │
│   API Routers · Services · ML Models · DuckDB     │
└──────────────────────────────────────────────────┘
```

### How They Connect

- The **Tauri shell** (Rust) creates the native window and manages the Python engine process.
- The **React frontend** renders inside that window and communicates with the engine via HTTP REST on `localhost:44945`.
- The **FastAPI engine** handles all data processing, analytics, ML inference, and database operations.

There is no WebSocket or gRPC — just plain HTTP/JSON over localhost. This keeps things simple and debuggable.

---

## Layer 1: Tauri Shell (Rust)

**Location**: `desktop/src-tauri/`

### Responsibilities

1. **Window Management** — Creates a splash window (780×380, transparent) and a main window (1280×800, min 960×600). Custom title bar (no OS decorations).
2. **Engine Lifecycle** — In production builds, Tauri starts the bundled `novem-engine.exe` as a child process before showing the main window. On app close, it sends a shutdown signal and force-kills after 5 seconds if needed.
3. **Environment Setup** — Passes data and config directory paths to the engine via environment variables (`NOVEM_DATA_DIR`, `NOVEM_CONFIG_DIR`).
4. **Port Management** — Checks if port `44945` is already in use before starting the engine. Skips engine launch if the port is occupied (useful when running the engine manually in development).

### Dev vs Production Behavior

| Behavior | Development (`tauri dev`) | Production (`tauri build`) |
|---|---|---|
| Engine start | Skipped (you run it manually) | Auto-launches `novem-engine.exe` |
| Data directory | `engine/data/` | `%APPDATA%/com.novem.desktop/data/` |
| Config directory | `engine/config/` | `%APPDATA%/com.novem.desktop/config/` |
| DevTools | Opened automatically | Disabled |

### Key File

- `src/lib.rs` — All engine management logic. Uses `cfg!(debug_assertions)` to switch between dev and prod behavior.

---

## Layer 2: Desktop Frontend (React + TypeScript)

**Location**: `desktop/src/`

### Core Architecture

The frontend follows a clean separation of concerns:

```
Pages (data orchestration + layout)
  └── Hooks (API calls + state writes)
        └── Stores (cached state)
              └── Components (pure rendering)
                    └── API Client (HTTP transport)
```

### Routing

React Router v6 with `HashRouter` and 18 routes. All page components are **lazy-loaded** with `React.lazy()` for code splitting.

```
/                   → Splash screen
/landing            → First-time landing carousel
/welcome            → Setup wizard (4 steps)
/login              → Authentication screen
/store-switcher     → Store selection grid
/dashboard          → KPI overview + trends
/customers          → Customer analytics
/products           → Product analytics
/marketing          → Marketing analytics
/insights           → Intelligence feed
/forecasting        → Time-series forecasts
/sentiment          → Sentiment analysis
/copilot            → AI chat
/import             → Data import wizard
/data-viewer        → Browse raw data
/stores             → Store management
/reports            → Export & reports
/settings           → App settings
```

### Auth Gate

Before reaching the main app, every request passes through an **Auth Gate** in `App.tsx`:
1. Is the user profile set up? → No → redirect to `/welcome`
2. Is there a valid session? → No → redirect to `/login`
3. Does password policy require re-auth? → Yes → redirect to `/login`
4. Is a store selected? → No → redirect to `/store-switcher`
5. All clear → render the requested page inside `AppShell`

### State Management Pattern

Zustand stores are the backbone. There are 16 stores, each owning a specific domain:

| Store | Purpose |
|---|---|
| `appStore` | Global state: theme, engine status, active module, zoom, command palette |
| `authStore` | Authentication, session management, password policies |
| `settingsStore` | User preferences (persisted to localStorage) |
| `storeStore` | Active store, store list, CRUD operations |
| `dashboardStore` | KPI data, period selection, trends |
| `customerStore` | Customer analytics cache |
| `productStore` | Product analytics cache |
| `marketingStore` | Marketing data cache |
| `insightStore` | Insights, anomalies, health score |
| `forecastStore` | Forecast results and filters |
| `sentimentStore` | Sentiment analysis data |
| `copilotStore` | Chat history, Ollama model config |
| `importStore` | Import wizard state (multi-step flow) |
| `alertStore` | Alerts and notification cache |
| `dataAvailabilityStore` | Which tables have data for the active store |
| `syncStore` | Sync timestamps and status |

**Rule**: Stores hold state. Hooks call APIs and write results to stores. Components read from stores. Stores never call APIs directly.

### Data Flow

```
User action → Component → Hook → API Client → Engine → DuckDB/SQLite
                                     ↓
                              Zustand Store ← Response
                                     ↓
                              Component re-render
```

### Styling Approach

- **CSS Modules** (`.module.css`) for component-scoped styles — no utility classes, no CSS-in-JS
- **CSS Custom Properties** defined in `variables.css` — spacing, colors, typography, shadows, transitions (all on a 4px grid)
- **Ant Design ConfigProvider** for global theming — token overrides for brand green accent
- **Dark and Light modes** — Pure black (#0e0e0e) dark theme, clean white (#ffffff) light theme

### Charts

All data visualization uses **ECharts** via `echarts-for-react`. No Chart.js, no Recharts, no D3 directly. Chart options are built inline in each component.

---

## Layer 3: Compute Engine (FastAPI / Python)

**Location**: `engine/app/`

### Core Architecture

```
API Routers (22 routers, 93+ endpoints)
  └── Services (14 service modules)
        ├── Analytics (KPIs, trends, forecasting)
        ├── ML Models (churn, basket, lifecycle, anomaly)
        ├── NLP (sentiment, copilot RAG)
        ├── Ingestion (parsing, cleaning, merging)
        └── Infrastructure (email, export, sync)
              └── Core (database, encryption, middleware, scheduler)
                    └── Databases (DuckDB + SQLite)
```

### Request Lifecycle

1. Request hits FastAPI
2. `RequestIdMiddleware` attaches a unique trace ID (`X-Request-Id`)
3. `RequestLoggingMiddleware` logs method, path, status, duration
4. `AuthMiddleware` validates session token (skips health check and webhook endpoints)
5. Router function executes, calling service layer
6. Service queries DuckDB/SQLite, runs ML models, returns results
7. Response wrapped in standard format: `{ success, data, error }`
8. `X-NOVEM-API-Version: 1` header added to response

### Database Strategy

NOVEM uses two databases for two distinct purposes:

| Database | Engine | Purpose | Location |
|---|---|---|---|
| DuckDB | OLAP | All analytical data (orders, customers, products, etc.) | `data/analytics.duckdb` |
| SQLite | OLTP | Metadata, config, auth, sessions | `data/metadata.sqlite` |

**Why two databases?** DuckDB is an analytical columnar database — it is extremely fast for aggregations, time-series queries, and scans over millions of rows. SQLite is perfect for small transactional workloads like user settings and session management. Using both keeps each database doing what it does best.

### Store Isolation

All analytical data is scoped by `store_id`. This means:
- A user can have multiple stores (e.g., their Shopify store and their Amazon store)
- Each store's data is completely isolated
- Switching stores in the UI just changes which `store_id` is passed to API calls

### Thread Safety

Both databases use thread-safe connection patterns:
- **DuckDB**: Shared singleton connection, but each API call gets its own `cursor()` (isolated execution context)
- **SQLite**: `threading.local()` gives each thread its own connection with WAL mode

### Background Services

| Service | What It Does |
|---|---|
| Ollama Health Poller | Checks LLM availability every 60 seconds |
| APScheduler | Runs recurring data syncs (Shopify) |
| Recycle Bin Cleanup | Auto-purges deleted datasets older than 30 days on startup |
| Export File Cleanup | Removes export files older than 1 hour |

---

## Communication Protocol

### API Contract

Every API response follows this shape:

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
    "code": "INSUFFICIENT_DATA",
    "detail": "Need at least 90 days of order history for forecasting"
  }
}
```

### Pagination

Paginated endpoints return:
```json
{
  "data": [ ... ],
  "total": 1250,
  "page": 1,
  "pageSize": 50
}
```

### Date Format

All dates are ISO 8601 strings (`2026-04-13T14:30:00Z`). The frontend formats them according to the user's regional settings.

### Currency

Currency values are always numbers (not strings). The frontend applies formatting and conversion using the user's selected currency and live exchange rates from the ECB (via frankfurter.app API).

---

## Security Architecture

### Authentication

- Single-user model (this is a desktop app, not SaaS)
- Passwords hashed with **bcrypt**
- Session tokens generated with `secrets.token_urlsafe(32)`, 24-hour TTL
- Password policies: `never` (no lock screen), `on_startup` (login on each launch), `monthly`
- Login rate limiting: 5 attempts per 15-minute window

### Data Protection

- **PII Masking**: Customer emails and names are SHA-256 hashed on import by default
- **Credential Encryption**: All stored API keys and database passwords encrypted with Fernet (AES-128-CBC)
- **Encryption Key**: Generated once, stored with `0o600` file permissions
- **No Cloud**: All data stays on the local machine — nothing is sent anywhere

### SQL Safety

- All DuckDB and SQLite queries use **parameterized statements** — no string concatenation
- Table names validated against an allowlist before use
- Database connector enforces read-only queries (SELECT/WITH/EXPLAIN/SHOW only)
- No `eval()`, `exec()`, or `Function()` anywhere in the codebase

### CORS

The FastAPI server only accepts requests from:
- `http://localhost:1420` (Vite dev server)
- `http://localhost:5173` (Vite alternate port)
- `tauri://localhost` (Tauri production)

---

## Data Pipeline Architecture

### Import Flow

```
Source → Parse → Detect → Preview → Confirm → Clean → Merge → Store
```

1. **Source**: File upload (CSV/TSV/Excel), Google Sheets URL, Shopify API, PostgreSQL, MySQL
2. **Parse**: Auto-detect delimiter, encoding, header row
3. **Detect**: Pattern-based schema detection (orders? customers? products?) + column mapping via synonym matching and Levenshtein fuzzy matching
4. **Preview**: Show user 10 sample rows with proposed schema
5. **Confirm**: User approves or adjusts column mappings
6. **Clean**: Strip whitespace, normalize nulls, parse dates, clean numerics, normalize currency, normalize ad channels, mask PII
7. **Merge**: UPSERT into DuckDB using natural keys (order_id, customer_id, etc.)
8. **Store**: Save import history and lineage to SQLite for audit trail

### Quality Scoring

Every import gets an 8-point quality score (0-100):

| Check | Weight | What It Measures |
|---|---|---|
| Null Rate | 0.15 | Percentage of null values across columns |
| Duplicate Rate | 0.15 | Percentage of duplicate rows |
| Date Validity | 0.15 | Whether date columns parse correctly |
| Negative Values | 0.1 | Unexpected negative numbers in numeric columns |
| Currency Consistency | 0.1 | Mixed currency formats |
| Schema Match | 0.15 | How well columns match the expected schema |
| Row Count | 0.1 | Whether the dataset has a reasonable number of rows |
| Data Freshness | 0.1 | Whether the data is recent enough to be useful |

Score tiers: **Healthy** (≥80), **Needs Review** (≥50), **Poor** (<50).

---

## ML/Analytics Architecture

All models run locally — no API calls to external ML services.

| Model | Library | Purpose |
|---|---|---|
| KPI Calculator | DuckDB SQL | 10 KPIs with period comparison |
| Anomaly Detection | scipy (Z-score) | Rolling Z-score with 30-day window, 2.5σ threshold |
| Forecasting | Prophet | Time-series forecasting with confidence intervals |
| Churn Prediction | lifetimes (BG/NBD) | Customer lifetime value and churn probability |
| Basket Analysis | mlxtend | Association rules (frequent itemsets) |
| Feature Importance | SHAP | Explain which factors drive a metric |
| Sentiment | TextBlob | Review polarity scoring |
| Lifecycle Classification | scikit-learn | BCG-inspired product lifecycle (star, cash cow, question mark, dog) |
| Business DNA | Custom | 6-dimension radar fingerprint + archetype classification |
| Causal Breakdown | DuckDB SQL | Revenue decomposition into volume, price, interaction, refunds, channel, category components |

### Copilot (Local AI)

The AI Copilot uses **Ollama** running locally:
- 5 supported models: llama3.2, phi3:mini, qwen2.5:7b, qwen2.5-coder:7b, qwen2.5-coder:14b
- RAG context injection: pulls store overview, revenue data, customer metrics, products, reviews, channels before each query
- Fallback: If Ollama is not running, the Copilot uses rule-based pattern matching with 11 SQL templates
- Rate limiting: 30 messages per minute per session, 500 word max per message
