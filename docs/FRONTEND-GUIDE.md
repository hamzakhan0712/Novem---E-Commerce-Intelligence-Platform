# Frontend Guide

This document covers how the React + TypeScript frontend is organized, how to work with it, and the patterns used throughout.

---

## Stack

| Technology | Version | Role |
|---|---|---|
| React | 19 | UI framework |
| TypeScript | Strict mode | Type safety |
| Ant Design | 6 | Component library (buttons, tables, forms, modals, etc.) |
| ECharts | 6 | All charts and data visualization |
| Zustand | 5 | State management |
| React Router | 6 | Client-side routing |
| Axios | 1.14 | HTTP client |
| Vite | 8 | Build tool and dev server |
| Immer | 11 | Immutable state updates in Zustand stores |

---

## Directory Structure

```
desktop/src/
├── App.tsx              # Root component — routing + auth gate
├── main.tsx             # Entry point — mounts React
├── assets/              # Static images and fonts
├── components/          # 186 UI components across 11 modules
│   ├── shared/          # Reusable components (DataTable, EmptyState, etc.)
│   ├── shell/           # App frame (TitleBar, ActivityBar, StatusBar, etc.)
│   ├── dashboard/       # Dashboard-specific components
│   ├── customers/       # Customer analytics components
│   ├── products/        # Product analytics components
│   ├── marketing/       # Marketing components
│   ├── insights/        # Insights + anomaly components
│   ├── forecasting/     # Forecast chart + table
│   ├── sentiment/       # Sentiment analysis components
│   ├── copilot/         # AI chat components
│   ├── import/          # Data import wizard components
│   └── settings/        # Settings panel components
├── constants/           # Route paths + theme tokens
├── hooks/               # 15 custom data-fetching hooks
├── pages/               # 14+ page-level components
├── stores/              # 16 Zustand stores
├── styles/              # CSS variables + global styles
├── types/               # TypeScript interfaces
└── utils/               # API client, formatters, helpers
```

---

## Routing

The app uses `HashRouter` (for Tauri compatibility — file:// protocol doesn't support HTML5 history).

All page components are **lazy-loaded** with `React.lazy()` for code splitting:

```typescript
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Customers = lazy(() => import('./pages/Customers'));
// ...etc
```

### Route Definitions

| Path | Page | Auth Required | Description |
|---|---|---|---|
| `/` | Splash | No | Initial loading screen |
| `/landing` | Landing | No | First-time carousel introduction |
| `/welcome` | Welcome | No | 4-step setup wizard |
| `/login` | Login | No | Password authentication |
| `/store-switcher` | StoreSwitcher | Yes | Select active store |
| `/dashboard` | Dashboard | Yes | Main KPI dashboard |
| `/customers` | Customers | Yes | Customer analytics |
| `/products` | Products | Yes | Product analytics |
| `/marketing` | Marketing | Yes | Ad spend analytics |
| `/insights` | Insights | Yes | Intelligence feed |
| `/forecasting` | Forecasting | Yes | Time-series forecasts |
| `/sentiment` | Sentiment | Yes | Review analysis |
| `/copilot` | Copilot | Yes | AI chat |
| `/import` | ImportData | Yes | Data import wizard |
| `/data-viewer` | DataViewer | Yes | Browse raw data |
| `/stores` | Stores | Yes | Store management |
| `/reports` | Reports | Yes | Export and reports |
| `/settings` | Settings | Yes | Preferences |

### Auth Gate Logic

`App.tsx` wraps authenticated routes in an `AuthGate` that checks:

1. **Is profile set up?** → No → redirect to `/welcome`
2. **Is there a valid session?** → No → redirect to `/login`
3. **Password policy check** → `on_startup`: require password each launch. `monthly`: require once per month. `never`: auto-login.
4. **Is a store selected?** → No → redirect to `/store-switcher`

---

## Component Patterns

### Page Components

Page components live in `src/pages/`. Each one:
- Is a **default export** (for lazy loading)
- Fetches data via a custom hook (e.g., `useDashboardData()`)
- Composes a layout using module-specific components
- Handles loading, error, and empty states
- Does NOT contain business logic

```typescript
// pages/Dashboard.tsx (simplified)
export default function Dashboard() {
  const { kpis, trends, loading } = useDashboardData();
  
  if (loading) return <LoadingSkeleton type="kpi-row" />;
  
  return (
    <div className={styles.page}>
      <KpiGrid kpis={kpis} />
      <TrendChart data={trends} />
    </div>
  );
}
```

### Shared Components

Reusable components in `src/components/shared/`. These are used across multiple pages:

| Component | Purpose |
|---|---|
| `DataTable` | Ant Design Table wrapper with optional CSV export button |
| `EmptyState` | Placeholder when no data exists (icon + title + description + action) |
| `LoadingSkeleton` | Animated placeholders during loading (variants: `kpi-row`, `card-grid`, `chart`, `table`) |
| `PageErrorBoundary` | Error boundary with "Go to Dashboard" and "Reload" buttons |
| `HealthBadge` | Color-coded dot badge (green ≥80, amber ≥50, red <50) |
| `StatusBadge` | Color-coded label for order status (completed, pending, refunded, etc.) |
| `AlertPanel` | Popover notification dropdown with severity-colored cards |
| `DataGate` | Wrapper that checks if data is available before rendering children |
| `ExportButton` | One-click export button for any data table |
| `StoreSelector` | Dropdown to switch active store |

All shared components are exported from a barrel file: `src/components/shared/index.ts`.

### Module-Specific Components

Each feature module has its own component folder (e.g., `src/components/dashboard/`). These are NOT exported via barrel files unless they need to be used elsewhere.

Examples from the dashboard module:

| Component | What It Renders |
|---|---|
| `KpiCard` | Single KPI metric with value, change %, sparkline, and optional tooltip |
| `TrendChart` | ECharts line chart for revenue/orders over time |
| `RevenueAtRiskCard` | Dollar clock showing at-risk revenue from overdue customers |
| `TopProductsCard` | Mini chart of top-selling products |
| `QuickInsightsCard` | Top 3 insights from the insight engine |
| `DataQualityCard` | Data quality score with progress bar |

### Shell Components

The app frame lives in `src/components/shell/`:

| Component | Purpose |
|---|---|
| `AppShell` | Main layout wrapper — title bar + activity bar + content area + status bar |
| `TitleBar` | Custom title bar with logo, menu bar (File/Edit/View/Tools/Help), window controls |
| `ActivityBar` | Left sidebar navigation — 11 module icons + settings at the bottom |
| `StatusBar` | Bottom bar — engine status, store selector, zoom controls, theme toggle |
| `CommandPalette` | Ctrl+K palette with navigation and appearance commands |
| `SyncBanner` | Top banner showing sync status when a connector sync is running |
| `AppTour` | First-time guided tour of the interface |

---

## State Management (Zustand)

### Philosophy

- One store per domain — never one giant store
- Stores hold **UI state** and **cached API data**
- Hooks call APIs and write to stores — stores never call APIs directly
- Components read from stores — never directly from API responses
- Use `immer` middleware for stores with deeply nested state

### Store List

| Store | Key State | Persisted? |
|---|---|---|
| `appStore` | Theme, engine status, active module, zoom level, command palette open | No |
| `authStore` | User profile, session token, setup status, password policy | No |
| `settingsStore` | Currency, date format, fiscal year, AI mode, PII masking | Yes (localStorage) |
| `storeStore` | Active store, store list | No |
| `dashboardStore` | Selected period, KPI data, trend cache | No |
| `customerStore` | Customer summary, segments, churn data, cohort data | No |
| `productStore` | Product summary, top products, basket results, lifecycle data | No |
| `marketingStore` | Marketing KPIs, channel data, campaign rankings | No |
| `insightStore` | Insights, anomalies, health score, business DNA, causal breakdown | No |
| `forecastStore` | Forecast results, selected metric, horizon | No |
| `sentimentStore` | Sentiment summary, reviews, keywords, rating breakdown | No |
| `copilotStore` | Chat messages, active model, model list, Ollama status | No |
| `importStore` | Upload state, file preview, schema detection, mapping, import results | No |
| `alertStore` | Alert list, unread count | No |
| `dataAvailabilityStore` | Which tables have data for the active store | No |
| `syncStore` | Last sync timestamp, sync running state | No |

### Store Pattern

```typescript
// stores/dashboardStore.ts (simplified pattern)
import { create } from 'zustand';

interface DashboardState {
  period: string;
  kpis: KpiData | null;
  loading: boolean;
  setPeriod: (period: string) => void;
  setKpis: (kpis: KpiData) => void;
  setLoading: (loading: boolean) => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  period: '30d',
  kpis: null,
  loading: false,
  setPeriod: (period) => set({ period }),
  setKpis: (kpis) => set({ kpis }),
  setLoading: (loading) => set({ loading }),
}));
```

---

## Custom Hooks

Every data concern has its own hook. The hook pattern:

1. Reads relevant state from the Zustand store
2. Calls the API via `apiClient`
3. Writes results to the store
4. Exposes `{ data, loading, error, refetch }` to the component

### Hook List

| Hook | Data It Fetches |
|---|---|
| `useEngineHealth` | Polls `/health` every 1.5s, updates `appStore.engineStatus` |
| `useDashboardData` | KPIs, trends, revenue-at-risk, quality scores |
| `useCustomerData` | Customer summary, top customers, segments, growth, churn, cohort |
| `useProductData` | Product summary, top products, categories, lifecycle, basket, inventory |
| `useMarketingData` | Marketing KPIs, channels, trends, campaigns, wasted spend |
| `useInsightData` | Insights, anomalies, actions, feed, health score, drivers, DNA |
| `useForecastData` | Forecast results and metrics overview |
| `useSentimentData` | Sentiment summary, ratings, trends, reviews, keywords |
| `useCopilotData` | Chat state, model management, status |
| `useAlertData` | Alert list, unread count, mark-read actions |
| `useDataProfile` | Column-level data profiling for imported datasets |
| `useDataQuality` | Data quality scores |
| `useDataViewer` | Table browsing, column info, export |
| `useReportGenerator` | Report generation status |
| `useStores` | Store CRUD, active store management |

### Hook Pattern

```typescript
// hooks/useDashboardData.ts (simplified)
export function useDashboardData() {
  const { period, setKpis, setLoading } = useDashboardStore();
  const { activeStore } = useStoreStore();

  useEffect(() => {
    if (!activeStore) return;
    setLoading(true);
    apiClient.get('/dashboard/kpis', { 
      params: { store_id: activeStore.id, period } 
    })
    .then(res => setKpis(res.data.data))
    .finally(() => setLoading(false));
  }, [activeStore, period]);

  return { kpis: useDashboardStore(s => s.kpis), loading, period };
}
```

---

## API Client

`src/utils/apiClient.ts` creates an Axios instance with:

- **Base URL**: `VITE_ENGINE_URL` env var or `http://127.0.0.1:44945`
- **Timeout**: 30 seconds
- **Retry**: Up to 2 retries on network error or HTTP 503
- **Error Handling**: Standardizes error responses into `{ code, detail }` shape
- **401 Interceptor**: Clears session and redirects to login on unauthorized responses

---

## TypeScript Types

All types live in `src/types/`. Naming conventions:

- Response types end with `Response`: `DashboardResponse`, `CustomerListResponse`
- Request types end with `Request`: `ImportFileRequest`, `ForecastRequest`
- No `I` prefix on interfaces: `KpiData`, not `IKpiData`
- Enums use PascalCase: `DataType`, `HealthTier`
- Union literals are preferred over enums for simple cases

### Type Files

| File | Key Types |
|---|---|
| `api.ts` | `ApiResponse<T>`, `ApiError`, `PaginatedData<T>`, `HealthResponse` |
| `auth.ts` | `User`, `Session`, `PasswordPolicy` |
| `dashboard.ts` | `KpiData`, `KpiValue`, `TrendPoint`, `DashboardPeriod`, `AtRiskCustomer` |
| `customers.ts` | `CustomerSummary`, `CustomerSegment`, `ChurnPrediction`, `CohortData` |
| `products.ts` | `ProductSummary`, `BasketRule`, `LifecycleProduct`, `CategoryBreakdown` |
| `marketing.ts` | `MarketingKpis`, `ChannelData`, `CampaignData` |
| `insights.ts` | `Insight`, `Anomaly`, `HealthScore`, `BusinessDna`, `CausalDriver` |
| `forecasting.ts` | `ForecastResult`, `ForecastPoint`, `ForecastMetrics` |
| `sentiment.ts` | `SentimentSummary`, `Review`, `KeywordData` |
| `copilot.ts` | `ChatMessage`, `OllamaModel`, `ConversationStarter` |
| `ingestion.ts` | `DataPreview`, `DetectedSchema`, `ColumnMapping`, `HealthCheckDetail` |
| `store.ts` | `Store`, `StoreStatus` |
| `quality.ts` | `DataQuality`, `ColumnQuality` |

---

## Charts (ECharts)

All charts use `echarts-for-react`. The pattern:

```typescript
import ReactECharts from 'echarts-for-react';

function TrendChart({ data }: { data: TrendPoint[] }) {
  const option = {
    xAxis: { type: 'category', data: data.map(d => d.date) },
    yAxis: { type: 'value' },
    series: [{ data: data.map(d => d.value), type: 'line' }],
  };

  return <ReactECharts option={option} style={{ height: 300 }} />;
}
```

Chart color palette is defined in `src/constants/theme.ts`:
```
#52c41a (green — brand accent)
#1677ff (blue)
#722ed1 (purple)
#13c2c2 (teal)
#fa8c16 (orange)
#eb2f96 (pink)
#fadb14 (yellow)
#ff4d4f (red)
```

---

## Styling

### CSS Modules

Every component gets its own `.module.css` file:

```css
/* Dashboard.module.css */
.page { padding: var(--novem-space-6); }
.kpiGrid { display: grid; grid-template-columns: repeat(5, 1fr); gap: var(--novem-space-4); }
```

```typescript
import styles from './Dashboard.module.css';
<div className={styles.page}>
```

### Design Tokens

All design values come from CSS custom properties in `src/styles/variables.css`:

- **Spacing**: 4px grid (`--novem-space-1` through `--novem-space-12`)
- **Colors**: Brand green accent, semantic colors (success, warning, error, info)
- **Typography**: Inter font, sizes from 11px to 36px
- **Shadows**: 5 elevation levels (xs through xl)
- **Transitions**: fast (100ms), base (200ms), slow (300ms), spring (400ms)
- **Border radius**: sm (4px), md (6px), lg (8px), xl (12px), full (9999px)

### Theming

Two themes: dark and light. The theme is toggled via `settingsStore.theme` and applied through Ant Design's `ConfigProvider`:

- **Dark**: Pure black background (`#0e0e0e`), no blue tints
- **Light**: Clean white background (`#ffffff`)

---

## Import Structure

Follow this order in every file:

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

// 5. Components
import { KpiCard } from '@/components/shared/KpiCard';
import { PeriodSelector } from './PeriodSelector';

// 6. Types
import type { KpiData } from '@/types/dashboard';

// 7. Utils and constants
import { formatCurrency } from '@/utils/formatCurrency';

// 8. Styles
import styles from './Dashboard.module.css';
```

Use the `@/` path alias (points to `src/`). Never go up more than one level in relative imports (`../../` is the max).

---

## Currency Formatting

`src/utils/formatCurrency.ts` handles all currency display:

- `formatCurrency(value)` — Full format with symbol (e.g., "$1,234.56")
- `formatCurrencyCompact(value)` — Abbreviated (e.g., "$1.2K")
- `setExchangeRate(rate, currency)` — Updates the module-level conversion rate

The active exchange rate is fetched from the ECB (via frankfurter.app) and cached. All components use these functions — no hardcoded `$` symbols anywhere.

---

## Key Decisions and Why

**Why HashRouter instead of BrowserRouter?**
Tauri loads the frontend from `file://` protocol. HTML5 history mode doesn't work with file-based URLs, so we use hash-based routing (`/#/dashboard`).

**Why Zustand instead of Redux?**
Zustand is simpler, has less boilerplate, and works naturally with React hooks. For a desktop app with 16 stores, Redux's ceremony would be overkill.

**Why CSS Modules instead of Tailwind?**
CSS Modules provide full scoping without adding thousands of utility classes to the HTML. They're easier to read and maintain for a component library this size.

**Why ECharts instead of Chart.js?**
ECharts handles large datasets better, has richer interactivity out of the box, and supports more chart types (radar, heatmap, treemap) needed for features like Business DNA and Cohort Replay.

**Why no barrel files for pages?**
Pages are lazy-loaded with `React.lazy(() => import('./pages/Dashboard'))`. Barrel files would break code splitting by pulling all pages into one bundle.
