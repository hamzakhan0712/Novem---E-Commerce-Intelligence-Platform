<p align="center">
  <img src="docs/images/novem.png" alt="NOVEM - E-Commerce Intelligence Platform" width="100%">
</p>

# NOVEM — E-Commerce Intelligence Platform

## What is NOVEM?

NOVEM is a local-first desktop application that brings data science to small and medium e-commerce businesses. It auto-profiles your data, calculates KPIs, runs ML models, detects anomalies, and generates plain-language insights — all on your own machine, with no subscriptions, no cloud dependency, and no data leaving your computer.

Think of it as having a personal data analyst sitting inside a desktop app.

---

## Why NOVEM Exists

Most e-commerce analytics tools are either:
- **Too expensive** — Enterprise BI platforms charge hundreds per month
- **Too basic** — Shopify/WooCommerce built-in analytics only scratch the surface
- **Too complex** — Open-source data tools require engineering skills
- **Cloud-dependent** — Your sensitive business data lives on someone else's servers

NOVEM solves all four problems. It is free, powerful, approachable, and fully offline.

---

## What It Can Do

| Capability | Description |
|---|---|
| **Dashboard** | 10+ KPIs with period comparison, trend charts, anomaly markers |
| **Customer Intelligence** | RFM segmentation, churn prediction, cohort analysis, customer stories |
| **Product Analytics** | Basket analysis, lifecycle classification, inventory optimization, stock forecasting |
| **Marketing Analytics** | Channel ROI, campaign ranking, ad spend trends, wasted spend detection |
| **Insights Engine** | Auto-generated insights, causal breakdowns, missed revenue detection, business health score |
| **Forecasting** | Prophet-based time-series forecasting with confidence intervals |
| **Sentiment Analysis** | Review scoring, keyword extraction, product-level sentiment trends |
| **AI Copilot** | Natural language Q&A powered by local Ollama LLM with RAG context |
| **Multi-Source Import** | CSV, Excel, Google Sheets, Shopify API, PostgreSQL, MySQL |
| **Data Quality** | 8-point quality scoring, PII masking, column profiling |
| **Reports** | CSV export, narrative reports, PDF generation |

---

## Tech Stack at a Glance

| Layer | Technology |
|---|---|
| Desktop Shell | Tauri v2 (Rust) |
| Frontend | React 19 + TypeScript + Ant Design 6 + ECharts |
| State Management | Zustand |
| Backend | FastAPI (Python 3.12) |
| Analytical DB | DuckDB |
| Metadata DB | SQLite |
| ML | scikit-learn, Prophet, mlxtend, lifetimes, SHAP |
| NLP/Sentiment | TextBlob |
| Local AI | Ollama (optional) |
| Build | Vite (frontend), PyInstaller (engine), NSIS (installer) |

---

## Project Structure

```
Novem---E-Commerce-Intelligence-Platform/
├── desktop/              # React + Tauri frontend application
│   ├── src/              # React source code
│   │   ├── components/   # 186 UI components across 11 modules
│   │   ├── pages/        # 14 page-level components
│   │   ├── hooks/        # 15 data-fetching hooks
│   │   ├── stores/       # 16 Zustand state stores
│   │   ├── types/        # 14 TypeScript type definitions
│   │   ├── utils/        # API client, date helpers, currency formatting
│   │   └── styles/       # CSS variables and global styles
│   └── src-tauri/        # Rust shell (window management, engine lifecycle)
│
├── engine/               # Python FastAPI backend
│   ├── app/
│   │   ├── api/          # 22 API routers (93+ endpoints)
│   │   ├── core/         # Database, encryption, middleware, scheduler
│   │   ├── models/       # Pydantic data models
│   │   └── services/     # 14 service modules (analytics, ML, ingestion)
│   ├── config/           # Email configuration
│   ├── data/             # DuckDB + SQLite databases (gitignored)
│   └── scripts/          # Engine build scripts
│
├── scripts/              # Top-level build orchestration
├── docs/                 # Project documentation (you are here)
└── novem.code-workspace  # VS Code multi-root workspace
```

---

## Quick Start

### Prerequisites

- **Node.js** 18+ and **pnpm**
- **Python** 3.11+ with pip
- **Rust** toolchain (for Tauri)
- **Ollama** (optional, for AI Copilot)

### Run in Development

```bash
# 1. Install frontend dependencies
cd desktop
pnpm install

# 2. Set up Python environment
cd ../engine
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt

# 3. Start the engine
python -m uvicorn app.main:app --host 127.0.0.1 --port 44945 --reload

# 4. In another terminal, start the frontend
cd desktop
pnpm dev                    # Vite dev server on :1420

# Or start everything together with Tauri:
cd desktop
pnpm start                  # Launches Tauri dev mode (engine + frontend)
```

### Build for Production

```powershell
# From project root
.\scripts\build-installer.ps1
# Output: desktop/src-tauri/target/release/bundle/nsis/NOVEM_1.0.0_x64-setup.exe
```

---

## Documentation Index

| Document | What It Covers |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture, layer interactions, data flow |
| [SETUP.md](SETUP.md) | Detailed development environment setup |
| [FEATURES.md](FEATURES.md) | Every feature explained in depth |
| [API-REFERENCE.md](API-REFERENCE.md) | All 93+ API endpoints with parameters and responses |
| [ENGINE-GUIDE.md](ENGINE-GUIDE.md) | Backend services, ML models, data pipeline |
| [FRONTEND-GUIDE.md](FRONTEND-GUIDE.md) | React components, state management, hooks |
| [DATA-MODEL.md](DATA-MODEL.md) | Database schemas (DuckDB + SQLite) |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Build pipeline, packaging, distribution |

---

## License

See [LICENSE](../LICENSE) for details.
