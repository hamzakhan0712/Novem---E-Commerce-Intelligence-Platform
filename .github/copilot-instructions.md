# NOVEM — Copilot Instructions

## Project Identity

- **Name**: NOVEM — E-Commerce Intelligence Platform
- **Type**: Local-first desktop application (Tauri v2) with embedded Python analytics engine
- **Purpose**: Brings data science to small/medium e-commerce businesses — auto-profiling, KPIs, ML models, anomaly detection, plain-language insights — all offline, no subscriptions

---

## Tech Stack Rules

### Desktop Frontend (Primary)
- **Framework**: React 18+ with TypeScript (strict mode)
- **UI Library**: Ant Design 5 — use Ant components as the base; do not install alternative component libraries
- **Charts**: ECharts via `echarts-for-react` — all data visualization uses ECharts, no Chart.js or Recharts
- **State**: Zustand — no Redux, no Context API for global state. Context is only for theme/locale providers
- **Build**: Vite — no webpack, no CRA
- **Shell**: Tauri v2 (Rust) — native window, file system access, child process management
- **Styling**: CSS Modules (`.module.css`) for component-scoped styles. Ant Design's `ConfigProvider` for theming. No Tailwind, no styled-components, no Emotion

### Compute Engine (Backend)
- **Framework**: FastAPI with uvicorn
- **Data Engine**: DuckDB for analytical queries, SQLite for metadata/config storage
- **ML Libraries**: scikit-learn, Prophet, mlxtend, lifetimes (BG/NBD), SHAP
- **NLP**: TextBlob (polarity scoring)
- **AI**: Ollama (local LLM), optional Gemini API (user provides own key)

---

## Naming Conventions

### Files & Folders
- **React components**: PascalCase — `KpiCard.tsx`, `CustomerTable.tsx`
- **Hooks**: camelCase with `use` prefix — `useKpiData.ts`, `useThemeMode.ts`
- **Zustand stores**: camelCase with `Store` suffix — `dashboardStore.ts`, `customerStore.ts`
- **Utilities**: camelCase — `formatCurrency.ts`, `dateHelpers.ts`
- **Constants**: camelCase file, UPPER_SNAKE_CASE exports — `constants.ts` → `export const MAX_HEALTH_SCORE = 100`
- **Python modules**: snake_case — `kpi_calculator.py`, `churn_model.py`
- **Python classes**: PascalCase — `ChurnPredictor`, `DataProfiler`
- **API routers**: snake_case with module prefix — `router_dashboard.py`, `router_customers.py`

### Variables & Functions
- **TypeScript**: camelCase for variables/functions, PascalCase for types/interfaces/enums
- **Python**: snake_case for variables/functions, PascalCase for classes
- **Boolean variables**: prefix with `is`, `has`, `should`, `can` — `isLoading`, `hasData`, `shouldRefresh`
- **Event handlers**: prefix with `handle` in components, `on` in props — `handleClick`, `onClick`

### Types & Interfaces
- **Prefix interfaces with `I`**: No. Use plain names — `KpiData`, not `IKpiData`
- **API response types**: suffix with `Response` — `DashboardResponse`, `CustomerListResponse`
- **API request types**: suffix with `Request` — `ImportFileRequest`, `ForecastRequest`

---

## Import Structure (TypeScript)

Order imports in every file:

```typescript
// 1. React and core libraries
import { useState, useEffect } from 'react';

// 2. Third-party libraries
import { Card, Table, Button } from 'antd';
import ReactECharts from 'echarts-for-react';

// 3. Zustand stores
import { useDashboardStore } from '@/stores/dashboardStore';

// 4. Custom hooks
import { useKpiData } from '@/hooks/useKpiData';

// 5. Components (from shared, then local)
import { KpiCard } from '@/components/shared/KpiCard';
import { PeriodSelector } from './PeriodSelector';

// 6. Types
import type { KpiData, PeriodRange } from '@/types/dashboard';

// 7. Utils and constants
import { formatCurrency } from '@/utils/formatCurrency';
import { KPI_LABELS } from '@/constants/kpis';

// 8. Styles
import styles from './Dashboard.module.css';
```

Use `@/` path alias pointing to `src/`. Never use relative paths that go up more than one level (`../../` is the max).

---

## Import Structure (Python)

```python
# 1. Standard library
import os
from datetime import datetime
from typing import Optional

# 2. Third-party
import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# 3. Local modules
from app.core.database import get_duckdb_connection
from app.models.kpi import KpiResult
```

---

## Error Handling

### Frontend
- API calls: wrap in try/catch. On error, show Ant Design `message.error()` with a user-friendly string. Never show raw error objects or stack traces to the user.
- Use a central `apiClient` (Axios or fetch wrapper) with response interceptors for common error codes (401 → reauth, 500 → generic error toast).
- Loading states: every data-fetching component must handle `loading`, `error`, and `empty` states explicitly.

### Backend
- FastAPI endpoints: raise `HTTPException` with appropriate status codes. 400 for bad input, 404 for missing resources, 422 for validation errors, 500 for internal errors.
- Never return raw Python tracebacks. Catch exceptions and return structured error responses: `{ "detail": "Human-readable message", "code": "ERROR_CODE" }`.
- ML model errors (insufficient data, convergence failures): catch gracefully and return a specific error code so the frontend can show contextual guidance (e.g., "Need at least 90 days of order history for forecasting").

### Logging
- Backend: use Python `logging` module. Log level INFO for request handling, WARNING for recoverable errors, ERROR for failures.
- Frontend: use `console.error` only for actual errors. No `console.log` in production code.

---

## API Communication

- All frontend ↔ backend communication uses HTTP REST over `localhost`.
- Base URL is set via environment variable, default `http://127.0.0.1:44945`.
- Request/response format: JSON. Dates as ISO 8601 strings. Currency values as numbers (not strings).
- Paginated endpoints return: `{ "data": [...], "total": number, "page": number, "pageSize": number }`.
- Every endpoint response includes a `success: boolean` field at the top level.

---

## Component Patterns

### Page Components
- One page component per route, placed in `src/pages/<ModuleName>/`.
- Page components fetch data (via hooks) and compose layout. They do not contain business logic.
- Page components are default-exported.

### Shared Components
- Reusable components live in `src/components/shared/`.
- Module-specific components live in `src/components/<ModuleName>/`.
- Every shared component is named-exported from an `index.ts` barrel file.

### Hooks
- Data-fetching hooks follow the pattern: `const { data, loading, error, refetch } = useXxx()`.
- Hooks that call the API use the central `apiClient` and handle loading/error state internally.
- One hook per data concern — `useKpiData`, `useCustomerSegments`, `useForecast`.

### Zustand Stores
- One store per module: `dashboardStore`, `customerStore`, `forecastStore`, `settingsStore`, etc.
- Stores hold UI state (selected period, active filters) and cached API responses.
- Stores never call APIs directly — hooks call APIs and write results to stores.
- Use `immer` middleware for stores with deeply nested state.

---

## Data Patterns

### DuckDB Usage
- DuckDB is the analytical query engine. All heavy data queries run through DuckDB.
- Use parameterized queries for all user inputs — never string-concatenate values into SQL.
- Tables follow the canonical schema defined in the database schema doc.

### SQLite Usage
- SQLite stores metadata: user profile, dataset registry, settings, import history, alert log.
- Never store analytical data in SQLite. Never run analytical queries against SQLite.

---

## Security Rules

- **No credentials in code**: API keys, database URIs, and secrets are stored in the local SQLite config table (encrypted) or environment variables. Never hardcode.
- **PII masking**: Customer emails and names are SHA-256 hashed on import by default. Raw PII is never stored unless the user explicitly disables masking.
- **SQL injection prevention**: All DuckDB and SQLite queries use parameterized statements. No string formatting for queries.
- **Input validation**: All API endpoints validate input via Pydantic models. All file paths are sanitized before access.
- **No eval/exec**: Never use `eval()`, `exec()`, or `Function()` constructor with user-provided strings.
- **CORS**: The FastAPI server only accepts requests from `localhost`. CORS is configured to reject all other origins.

---

## What NOT to Do

- Do not install additional UI component libraries (Material UI, Chakra, shadcn, etc.)
- Do not add ORMs (SQLAlchemy, Prisma). Use raw DuckDB/SQLite queries via their Python drivers
- Do not create class-based React components. Functional components with hooks only
- Do not use `any` type in TypeScript except at true system boundaries (e.g., parsing unknown JSON). Prefer `unknown` and narrow
- Do not create barrel files (`index.ts`) for pages — only for shared components
- Do not add features not described in the vision plan. If it's not in scope, it doesn't get built
- Do not add comments that restate what the code does. Comment only the "why" for non-obvious decisions
- Do not create wrapper abstractions around Ant Design components unless adding real behavior. Use Ant components directly
- Do not store computed analytics results in the database. Recompute from source data on demand (with caching in memory)
