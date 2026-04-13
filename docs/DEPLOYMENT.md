# Deployment & Build Guide

This document covers how to build NOVEM for production and distribute it as a Windows installer.

---

## Build Overview

NOVEM ships as a single Windows installer (`.exe`) created by NSIS (via Tauri). The installer bundles:

1. **Frontend** — React app compiled to static HTML/JS/CSS by Vite
2. **Rust shell** — Tauri binary that creates the native window and manages the engine
3. **Python engine** — Bundled as a standalone executable by PyInstaller (includes Python runtime + all dependencies)

The user installs one `.exe` and gets a fully working application with no additional setup.

---

## Architecture in Production

```
Installed App/
├── NOVEM.exe                    # Tauri binary (Rust)
├── resources/
│   └── engine/
│       └── novem-engine.exe     # PyInstaller bundle (Python + all deps)
└── (Webview2 runtime)           # Edge-based renderer
```

When the user launches `NOVEM.exe`:
1. Tauri shows the splash screen (transparent, 780×380)
2. Tauri starts `novem-engine.exe` as a child process
3. Tauri polls `http://127.0.0.1:44945/health` until the engine is ready
4. Tauri shows the main window (1280×800) with the React app
5. On app close: Tauri sends POST `/system/shutdown`, waits 5 seconds, then force-kills the engine

### Data Storage in Production

| What | Location |
|---|---|
| DuckDB (analytics) | `%APPDATA%/com.novem.desktop/data/analytics.duckdb` |
| SQLite (metadata) | `%APPDATA%/com.novem.desktop/data/metadata.sqlite` |
| Encryption key | `%APPDATA%/com.novem.desktop/data/encryption.key` |
| Engine log | `%APPDATA%/com.novem.desktop/data/engine.log` |
| Email config | `%APPDATA%/com.novem.desktop/config/email_config.json` |

The Tauri shell creates these directories on first launch and passes them to the engine via environment variables:
- `NOVEM_DATA_DIR` → `%APPDATA%/com.novem.desktop/data/`
- `NOVEM_CONFIG_DIR` → `%APPDATA%/com.novem.desktop/config/`

---

## Build Prerequisites

| Tool | Purpose |
|---|---|
| **pnpm** | Install frontend dependencies and build |
| **cargo** (Rust) | Compile the Tauri shell |
| **Python 3.11+** | Engine venv with all dependencies installed |
| **PyInstaller** | Bundle Python + deps into standalone exe |
| **NSIS** | Create Windows installer (handled by Tauri) |

---

## Full Build Process

### One Command

From the project root:

```powershell
.\scripts\build-installer.ps1
```

This runs the full 7-step pipeline:

### Step 1: Validate Prerequisites

Checks that `pnpm`, `cargo`, `python`, and `pyinstaller` are all available on PATH.

### Step 2: Generate Installer Branding

Creates the NSIS installer branding images:
- `icons/installer-header.bmp` (150×57)
- `icons/installer-sidebar.bmp` (164×314)

These are generated from the app logo using a helper script.

### Step 3: Build Python Engine

```powershell
cd engine
pyinstaller novem-engine.spec --noconfirm
```

This creates `engine/dist/novem-engine/` containing:
- `novem-engine.exe` — Main executable
- All Python packages and their native dependencies
- The entire runtime — users don't need Python installed

The PyInstaller spec file (`novem-engine.spec`) handles:
- Hidden imports for all project modules
- Data files (config templates)
- Console mode disabled (no terminal window)

**Output**: `engine/dist/novem-engine/novem-engine.exe`

### Step 4: Verify Engine Build

Checks that the engine executable exists and is non-zero size.

### Step 5: Install Frontend Dependencies

```powershell
cd desktop
pnpm install
```

### Step 6: Build Tauri App

```powershell
cd desktop
pnpm tauri build --config <override>
```

This does three things:
1. **Vite build**: Compiles React + TypeScript to optimized static files in `desktop/dist/`
2. **Cargo build**: Compiles the Rust Tauri shell in release mode (optimized, stripped, LTO)
3. **NSIS build**: Packages everything into a Windows installer

The `--config` override injects the engine resource path (pointing to `engine/dist/novem-engine/`) at build time. This isn't in `tauri.conf.json` directly because it would break `cargo check` during development.

### Step 7: Deploy Engine

Copies the engine build output next to the final release executable for standalone deployment support.

**Final Output**: `desktop/src-tauri/target/release/bundle/nsis/NOVEM_1.0.0_x64-setup.exe`

---

## Build Flags

```powershell
# Skip engine build (iterate on frontend/Rust only)
.\scripts\build-installer.ps1 -SkipEngine

# Debug build (unoptimized, faster compilation)
.\scripts\build-installer.ps1 -Debug
```

---

## Engine Build Separately

If you only need to rebuild the engine:

```powershell
cd engine
.\scripts\build_engine.ps1

# With clean (removes previous build artifacts)
.\scripts\build_engine.ps1 -Clean
```

**Steps**:
1. Activates the Python virtual environment
2. Optionally cleans previous `dist/` and `build/` directories
3. Runs PyInstaller with the project spec file
4. Verifies the output exists

---

## Dev vs Production: Key Differences

| Aspect | Development | Production |
|---|---|---|
| Engine start | Manual (`python -m uvicorn ...`) | Auto-launched by Tauri |
| Engine binary | Python source + venv | PyInstaller standalone exe |
| Frontend | Vite dev server (HMR on :1420) | Static files compiled by Vite |
| Data location | `engine/data/` | `%APPDATA%/com.novem.desktop/data/` |
| Config location | `engine/config/` | `%APPDATA%/com.novem.desktop/config/` |
| DevTools | Open by default | Disabled |
| Log level | Debug | Info |
| CORS | localhost:1420, localhost:5173 | tauri://localhost |
| Hot reload | Yes (Vite + uvicorn --reload) | No |

The switch is controlled by Rust's `cfg!(debug_assertions)`:
- `tauri dev` → debug mode → skips engine management
- `tauri build` → release mode → manages engine lifecycle

---

## Installer Configuration

NSIS installer settings (from `tauri.conf.json`):

| Setting | Value |
|---|---|
| Install mode | Both (per-user and per-machine) |
| Compression | LZMA |
| Installer icon | `icons/icon.ico` |
| Header image | `icons/installer-header.bmp` |
| Sidebar image | `icons/installer-sidebar.bmp` |
| Product name | NOVEM |
| Identifier | `com.novem.desktop` |
| Version | 1.0.0 |

The installer:
- Lets the user choose install location
- Creates desktop and start menu shortcuts
- Registers for clean uninstall via Add/Remove Programs
- Bundles WebView2 bootstrapper (Edge runtime) if not already installed

---

## Release Profile (Rust)

The Tauri binary is compiled with aggressive optimization:

```toml
[profile.release]
opt-level = "s"        # Optimize for binary size
lto = true             # Link-time optimization
codegen-units = 1      # Single codegen unit (slower compile, smaller binary)
```

---

## Port Configuration

The engine always runs on port **44945**. This is hardcoded in:
- `engine/app/config.py` (`ENGINE_PORT = 44945`)
- `desktop/src-tauri/src/lib.rs` (`const ENGINE_PORT: u16 = 44945`)
- `desktop/src/utils/apiClient.ts` (default base URL)

Before launching the engine in production, Tauri checks if this port is already occupied. If it is (e.g., user is running the engine in development), Tauri skips engine launch and connects to the existing instance.

---

## Graceful Shutdown

When the user closes the app:

1. Tauri's `on_window_event(WindowEvent::Destroyed)` fires
2. Tauri sends `POST http://127.0.0.1:44945/system/shutdown`
3. The engine:
   - Stops accepting new requests
   - Shuts down APScheduler
   - Closes DuckDB and SQLite connections
   - Exits the process
4. If the engine hasn't exited within 5 seconds, Tauri force-kills the process

---

## Troubleshooting Production Builds

### PyInstaller build fails

- Make sure the Python venv is activated and all requirements are installed
- Check that `engine/novem-engine.spec` lists all hidden imports
- Run `pyinstaller novem-engine.spec --noconfirm` manually to see detailed errors

### Tauri build fails during cargo compilation

- Run `cargo check` in `desktop/src-tauri/` to see Rust errors
- Make sure `engine/dist/novem-engine/` exists (even if empty) — Tauri's resource resolution needs it
- Check Rust version: `rustup show` — minimum 1.77.2

### Installer is too large

The installer is typically 80-120 MB. The breakdown:
- PyInstaller engine bundle: ~60-80 MB (includes Python runtime + numpy + pandas + scikit-learn + Prophet)
- Tauri binary: ~5-10 MB
- Frontend assets: ~3-5 MB
- NSIS packaging overhead: ~2 MB

To reduce size:
- The Rust release profile already uses `opt-level = "s"` and LTO
- PyInstaller excludes unnecessary packages via the spec file
- Vite tree-shakes unused JavaScript

### Engine won't start in production

- Check the engine log at `%APPDATA%/com.novem.desktop/data/engine.log`
- Verify the engine exe exists at `resources/engine/novem-engine.exe` relative to the Tauri binary
- Check if port 44945 is already in use: `netstat -ano | findstr 44945`

---

## Environment Variables

These environment variables can be used to override defaults:

| Variable | Default | Description |
|---|---|---|
| `VITE_ENGINE_URL` | `http://127.0.0.1:44945` | Frontend's engine base URL |
| `NOVEM_DATA_DIR` | `./data/` (dev) or `%APPDATA%/.../data/` (prod) | Database file directory |
| `NOVEM_CONFIG_DIR` | `./config/` (dev) or `%APPDATA%/.../config/` (prod) | Configuration file directory |
| `NOVEM_ENGINE_DIR` | (auto-detected) | Engine executable directory |
| `LOG_LEVEL` | `info` | Engine log level |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama LLM server URL |
