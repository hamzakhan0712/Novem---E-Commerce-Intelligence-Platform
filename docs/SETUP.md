# Development Setup Guide

This guide walks you through setting up the NOVEM development environment from scratch on a Windows machine. By the end, you'll have the engine running, the frontend rendering, and be ready to make changes.

---

## Prerequisites

You need the following installed on your machine before starting:

| Tool | Version | Purpose |
|---|---|---|
| **Node.js** | 18 or later | JavaScript runtime for the frontend |
| **pnpm** | 8 or later | Package manager (faster than npm) |
| **Python** | 3.11 or later | Backend engine runtime |
| **Rust** | 1.77+ | Tauri native shell compilation |
| **Git** | Any | Version control |
| **Ollama** | Latest (optional) | Local LLM for AI Copilot |

### Installing Prerequisites

```powershell
# Node.js — download from https://nodejs.org/
# Or via winget:
winget install OpenJS.NodeJS.LTS

# pnpm
npm install -g pnpm

# Python — download from https://www.python.org/
# Make sure to check "Add Python to PATH" during installation

# Rust toolchain
# Visit https://rustup.rs/ and run the installer
rustup default stable

# Ollama (optional — only needed for AI Copilot)
# Download from https://ollama.com/download
```

---

## Clone the Repository

```bash
git clone https://github.com/hamzakhan0712/Novem---E-Commerce-Intelligence-Platform.git
cd Novem---E-Commerce-Intelligence-Platform
```

---

## Step 1: Set Up the Python Engine

```powershell
cd engine

# Create a virtual environment
python -m venv .venv

# Activate it
.venv\Scripts\Activate.ps1          # PowerShell
# or: .venv\Scripts\activate          # Command Prompt
# or: source .venv/bin/activate       # macOS/Linux

# Install all dependencies
pip install -r requirements.txt
```

This installs ~30 packages including FastAPI, DuckDB, pandas, scikit-learn, Prophet, and more. It may take a few minutes.

### Verify the Engine

```powershell
# Start the engine
python -m uvicorn app.main:app --host 127.0.0.1 --port 44945 --reload

# You should see:
# INFO:     Started server process
# INFO:     Uvicorn running on http://127.0.0.1:44945
```

Visit `http://127.0.0.1:44945/health` in your browser. You should get:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "uptime": 1.23
  }
}
```

The engine auto-creates its database files on first run:
- `engine/data/analytics.duckdb` (DuckDB analytical database)
- `engine/data/metadata.sqlite` (SQLite metadata database)

---

## Step 2: Set Up the Frontend

Open a **new terminal** (keep the engine running in the first one):

```powershell
cd desktop

# Install Node.js dependencies
pnpm install
```

### Run the Frontend (Development)

You have three options:

#### Option A: Frontend Only (Hot Reload)

```powershell
cd desktop
pnpm dev
# Vite dev server starts on http://localhost:1420
```

This gives you the fastest hot-reload experience. The engine must already be running separately (Step 1).

#### Option B: Frontend + Engine Together

```powershell
cd desktop
pnpm dev:all
# Starts both the Python engine and Vite dev server via concurrently
```

This is convenient but you don't see engine logs as clearly.

#### Option C: Full Tauri Dev Mode

```powershell
cd desktop
pnpm start
# Compiles Rust code and opens the native Tauri window
```

This is the closest to how users will experience the app. First run takes longer because Rust needs to compile. Subsequent runs are faster.

---

## Step 3: Set Up Ollama (Optional)

If you want the AI Copilot to work:

```powershell
# Start Ollama service
ollama serve

# Pull a model (smallest one first)
ollama pull llama3.2
```

NOVEM checks Ollama status every 60 seconds. Once it detects Ollama running, the Copilot page becomes fully functional.

Supported models:
- `llama3.2` — 2.0 GB (default, recommended for most machines)
- `phi3:mini` — 2.2 GB
- `qwen2.5:7b` — 4.7 GB
- `qwen2.5-coder:7b` — 4.7 GB
- `qwen2.5-coder:14b` — 9.0 GB

---

## Step 4: Email Notifications (Optional)

To enable email alerts and verification:

1. Copy the example config:
   ```powershell
   cp engine/config/email_config.example.json engine/config/email_config.json
   ```

2. Edit `engine/config/email_config.json` with your SMTP credentials:
   ```json
   {
     "smtp_host": "smtp.gmail.com",
     "smtp_port": 587,
     "sender_email": "your-email@gmail.com",
     "sender_password": "your-app-password"
   }
   ```

   For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833), not your regular password.

3. Credentials are encrypted with Fernet on first use. The plaintext password is removed from the config file automatically.

---

## Project Layout for Development

### VS Code Workspace

Open `novem.code-workspace` in VS Code. This sets up a multi-root workspace with both `desktop/` and `engine/` as separate roots, giving you proper IntelliSense for both TypeScript and Python.

### Key Development Files

| What | Where |
|---|---|
| Frontend entry point | `desktop/src/main.tsx` |
| App routing | `desktop/src/App.tsx` |
| API client config | `desktop/src/utils/apiClient.ts` |
| Engine entry point | `engine/app/main.py` |
| Engine config | `engine/app/config.py` |
| Database schemas | `engine/app/core/database.py` |
| CSS design tokens | `desktop/src/styles/variables.css` |
| Route constants | `desktop/src/constants/routes.ts` |
| Theme constants | `desktop/src/constants/theme.ts` |

### Port Usage

| Port | Service |
|---|---|
| `44945` | FastAPI engine |
| `1420` | Vite dev server |
| `11434` | Ollama (if installed) |

---

## Common Development Tasks

### Adding a New API Endpoint

1. Create or edit a router in `engine/app/api/router_<module>.py`
2. Create the service logic in `engine/app/services/<module>/`
3. Register the router in `engine/app/main.py` if it's new
4. Add TypeScript types in `desktop/src/types/<module>.ts`
5. Create a Zustand store action or hook to call it

### Adding a New Page

1. Create the page component in `desktop/src/pages/<PageName>.tsx`
2. Add the route constant in `desktop/src/constants/routes.ts`
3. Add the route in `desktop/src/App.tsx` (inside the auth gate)
4. Add the navigation item in `desktop/src/components/shell/ActivityBar.tsx`
5. Add the command in `desktop/src/components/shell/CommandPalette.tsx`

### Running Type Checks

```powershell
# Frontend TypeScript
cd desktop
pnpm tsc --noEmit

# Backend Python linting
cd engine
ruff check .
```

### Resetting the Database

If you need to start fresh (e.g., schema changed):

```powershell
# Delete database files
Remove-Item engine/data/analytics.duckdb -Force
Remove-Item engine/data/metadata.sqlite -Force

# Restart the engine — schemas will be recreated
python -m uvicorn app.main:app --host 127.0.0.1 --port 44945 --reload
```

### Loading Sample Data

Instead of importing real data, you can load the built-in sample dataset:

1. Start the engine and frontend
2. Complete the setup wizard (create profile + store)
3. Go to **Import Data** page
4. Click **Load Sample Data**

This generates ~5,000 orders, 1,200 customers, 150 products, and 800 reviews with realistic e-commerce patterns.

---

## Troubleshooting

### Engine won't start

- **Port already in use**: Another process is on port 44945. Kill it or change the port in `engine/app/config.py`.
- **Module not found**: Make sure the virtual environment is activated (`.venv\Scripts\Activate.ps1`).
- **DuckDB/SQLite errors**: Delete the database files and restart (see "Resetting the Database" above).

### Frontend shows "Engine Offline"

- The health poller (`useEngineHealth`) checks `http://127.0.0.1:44945/health` every 1.5 seconds.
- Make sure the engine is running and healthy.
- Check the browser console for CORS errors.

### Tauri window is blank

- First Rust compile takes 3-5 minutes. Wait for it to finish.
- If still blank after compilation, check the Vite dev server is running on port 1420.

### Ollama Copilot not responding

- Run `ollama serve` in a separate terminal.
- Pull at least one model: `ollama pull llama3.2`.
- Check Ollama status at `http://localhost:11434`.
- NOVEM polls Ollama every 60 seconds — wait for the next poll or restart the engine.

### TypeScript compilation errors

- Run `pnpm install` to make sure all dependencies are present.
- The project uses TypeScript strict mode. Make sure you're not using `any` types.
