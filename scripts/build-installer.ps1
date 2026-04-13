#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Build the NOVEM desktop application installer (Windows).

.DESCRIPTION
    End-to-end build pipeline:
      1. Validate prerequisites (pnpm, cargo, python, pyinstaller)
      2. Generate NSIS installer branding images (sidebar, header BMPs)
      3. Build the Python engine into a standalone executable
      4. Verify engine dist is ready for Tauri bundling
      5. Install frontend dependencies
      6. Build the Tauri application (frontend + Rust + NSIS installer)
      7. Deploy engine next to release exe for standalone testing
      8. Report output artifacts

.PARAMETER SkipEngine
    Skip the engine build step. Useful when iterating on frontend
    or Rust changes while the engine binary is unchanged.

.PARAMETER Debug
    Build in debug mode (unoptimised, larger output).

.EXAMPLE
    .\scripts\build-installer.ps1
    .\scripts\build-installer.ps1 -SkipEngine
    .\scripts\build-installer.ps1 -Debug
#>

param(
    [switch]$SkipEngine,
    [switch]$Debug
)

$ErrorActionPreference = "Stop"
$Root       = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$DesktopDir = Join-Path $Root "desktop"
$EngineDir  = Join-Path $Root "engine"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  NOVEM — Installer Build"               -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Prerequisites ───────────────────────────────────────────────

Write-Host "[1/7] Checking prerequisites..." -ForegroundColor Yellow

if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) {
    Write-Error "pnpm is not installed. Install with: npm install -g pnpm"
}
Write-Host "  pnpm : $(pnpm --version)" -ForegroundColor Gray

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Write-Error "Rust/Cargo is not installed. Install from https://rustup.rs"
}
Write-Host "  cargo: $(cargo --version)" -ForegroundColor Gray

$python = $null
if (Get-Command python -ErrorAction SilentlyContinue) { $python = "python" }
elseif (Get-Command python3 -ErrorAction SilentlyContinue) { $python = "python3" }
if (-not $python) {
    Write-Error "Python is not installed. Install Python 3.11+ from https://python.org"
}
Write-Host "  python: $(& $python --version 2>&1)" -ForegroundColor Gray

Write-Host "  All prerequisites found." -ForegroundColor Green

# ── Step 2: Generate installer branding assets ─────────────────────────

Write-Host ""
Write-Host "[2/7] Generating installer branding images..." -ForegroundColor Yellow
$AssetScript = Join-Path (Split-Path -Parent $PSCommandPath) "generate_installer_assets.ps1"
if (Test-Path $AssetScript) {
    & $AssetScript
} else {
    Write-Host "  Asset script not found, skipping." -ForegroundColor DarkGray
}

# ── Step 3: Build Engine ────────────────────────────────────────────────

if (-not $SkipEngine) {
    Write-Host ""
    Write-Host "[3/7] Building engine executable..." -ForegroundColor Yellow
    $BuildScript = Join-Path (Join-Path $EngineDir "scripts") "build_engine.ps1"
    & $BuildScript -Clean
    if ($LASTEXITCODE -ne 0) { Write-Error "Engine build failed" }
} else {
    Write-Host ""
    Write-Host "[3/7] Skipping engine build (-SkipEngine)." -ForegroundColor DarkGray
}

# ── Step 4: Verify engine dist ──────────────────────────────────────────

Write-Host ""
Write-Host "[4/7] Verifying engine dist for Tauri bundle..." -ForegroundColor Yellow

$EngineDist = Join-Path (Join-Path $EngineDir "dist") "novem-engine"
$EngineExe  = Join-Path $EngineDist "novem-engine.exe"

if (-not (Test-Path $EngineExe)) {
    Write-Error "Engine executable not found at $EngineExe. Run without -SkipEngine first."
}

$totalSize = [math]::Round(((Get-ChildItem -Recurse $EngineDist | Measure-Object -Property Length -Sum).Sum) / 1MB, 0)
Write-Host "  Engine dist: $EngineDist ($totalSize MB)" -ForegroundColor Gray
Write-Host "  Ready for bundling." -ForegroundColor Green

# ── Step 5: Frontend dependencies ───────────────────────────────────────

Write-Host ""
Write-Host "[5/7] Installing frontend dependencies..." -ForegroundColor Yellow
Push-Location $DesktopDir
try {
    pnpm install --frozen-lockfile
    if ($LASTEXITCODE -ne 0) { Write-Error "pnpm install failed" }
} finally {
    Pop-Location
}
Write-Host "  Dependencies installed." -ForegroundColor Green

# ── Step 6: Build Tauri ─────────────────────────────────────────────────

Write-Host ""
Write-Host "[6/7] Building Tauri application..." -ForegroundColor Yellow

# Copy engine dist into src-tauri/ so Tauri can bundle it using the list-
# format resource config, which preserves directory structure (the map-
# format with globs flattens everything, destroying _internal/).
$SrcTauriEngine = Join-Path (Join-Path $DesktopDir "src-tauri") "engine"
if (Test-Path $SrcTauriEngine) { Remove-Item -Recurse -Force $SrcTauriEngine }
Copy-Item -Path $EngineDist -Destination $SrcTauriEngine -Recurse
Write-Host "  Copied engine dist into src-tauri/engine/" -ForegroundColor Gray

# Inject engine resources via --config override so that tauri.conf.json
# stays clean for dev (cargo check / tauri dev don't need the engine dist).
# List-format resources preserve the original directory tree.
$ConfigOverride = Join-Path $DesktopDir "tauri-build-override.json"
@'
{
  "bundle": {
    "resources": [
      "engine/"
    ]
  }
}
'@ | Set-Content -Path $ConfigOverride -Encoding UTF8

Push-Location $DesktopDir
try {
    if ($Debug) {
        pnpm tauri build --debug --config $ConfigOverride
    } else {
        pnpm tauri build --config $ConfigOverride
    }
    if ($LASTEXITCODE -ne 0) { Write-Error "Tauri build failed" }
} finally {
    Pop-Location
    if (Test-Path $ConfigOverride) { Remove-Item $ConfigOverride -Force }
    # Clean up the temporary engine copy from src-tauri/
    if (Test-Path $SrcTauriEngine) { Remove-Item -Recurse -Force $SrcTauriEngine }
}
Write-Host "  Build complete." -ForegroundColor Green

# ── Step 7: Deploy engine for standalone exe ────────────────────────────

Write-Host ""
Write-Host "[7/8] Deploying engine next to release exe (standalone use)..." -ForegroundColor Yellow

$TauriTarget = Join-Path (Join-Path $DesktopDir "src-tauri") "target"
if ($Debug) {
    $ReleaseDir = Join-Path $TauriTarget "debug"
} else {
    $ReleaseDir = Join-Path $TauriTarget "release"
}
$StandaloneEngine = Join-Path $ReleaseDir "engine"

if (Test-Path $StandaloneEngine) { Remove-Item -Recurse -Force $StandaloneEngine }

Copy-Item -Path $EngineDist -Destination $StandaloneEngine -Recurse
Write-Host "  Copied engine to $StandaloneEngine" -ForegroundColor Gray
Write-Host "  Standalone exe + engine ready." -ForegroundColor Green

# ── Step 8: Report artifacts ────────────────────────────────────────────

Write-Host ""
Write-Host "[8/8] Build artifacts:" -ForegroundColor Yellow

if ($Debug) {
    $BundleDir = Join-Path (Join-Path $TauriTarget "debug") "bundle"
} else {
    $BundleDir = Join-Path (Join-Path $TauriTarget "release") "bundle"
}

if (Test-Path $BundleDir) {
    Get-ChildItem -Path $BundleDir -Recurse -File |
        Where-Object { $_.Extension -in ".exe", ".msi" } |
        ForEach-Object {
            $size = [math]::Round($_.Length / 1MB, 1)
            Write-Host "  $($_.Name)  ($size MB)" -ForegroundColor White
            Write-Host "    $($_.FullName)" -ForegroundColor Gray
        }
} else {
    Write-Host "  Bundle directory not found at $BundleDir" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Build finished successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Usage:" -ForegroundColor White
Write-Host "    Installer  : Run the NSIS .exe from the bundle directory" -ForegroundColor Gray
Write-Host "    Standalone : Run novem-desktop.exe from target\release\" -ForegroundColor Gray
Write-Host "                 (engine\ folder is deployed alongside it)" -ForegroundColor Gray
Write-Host ""
