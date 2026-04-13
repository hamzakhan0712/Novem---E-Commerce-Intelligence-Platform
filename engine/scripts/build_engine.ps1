#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Build the NOVEM compute engine into a standalone executable.

.DESCRIPTION
    Activates the Python virtual environment and runs PyInstaller to produce
    a standalone directory at engine/dist/novem-engine/ containing
    novem-engine.exe and all required runtime files.

.PARAMETER Clean
    Remove previous build artifacts before building.

.EXAMPLE
    .\scripts\build_engine.ps1
    .\scripts\build_engine.ps1 -Clean
#>

param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$EngineDir = Split-Path -Parent (Split-Path -Parent $PSCommandPath)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  NOVEM — Engine Build (PyInstaller)"    -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── Activate venv ───────────────────────────────────────────────────────

$VenvActivate = Join-Path $EngineDir ".venv\Scripts\Activate.ps1"
if (-not (Test-Path $VenvActivate)) {
    Write-Error "Python venv not found at $EngineDir\.venv. Create it first: python -m venv .venv && pip install -r requirements.txt"
}

Write-Host "[1/4] Activating virtual environment..." -ForegroundColor Yellow
& $VenvActivate

# Verify pyinstaller is available
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "  PyInstaller not found. Installing..." -ForegroundColor Yellow
    pip install pyinstaller
}
Write-Host "  PyInstaller: $(pyinstaller --version)" -ForegroundColor Gray

# ── Clean previous build ───────────────────────────────────────────────

if ($Clean) {
    Write-Host ""
    Write-Host "[2/4] Cleaning previous build artifacts..." -ForegroundColor Yellow
    $BuildDir = Join-Path $EngineDir "build"
    $DistDir  = Join-Path $EngineDir "dist"
    if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }
    if (Test-Path $DistDir)  { Remove-Item -Recurse -Force $DistDir  }
    Write-Host "  Cleaned." -ForegroundColor Green
} else {
    Write-Host "[2/4] Skipping clean (use -Clean to remove old artifacts)." -ForegroundColor DarkGray
}

# ── Build ───────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "[3/4] Running PyInstaller..." -ForegroundColor Yellow

Push-Location $EngineDir
try {
    $SpecFile = Join-Path $EngineDir "novem-engine.spec"
    pyinstaller $SpecFile --clean --noconfirm
    if ($LASTEXITCODE -ne 0) { Write-Error "PyInstaller build failed" }
} finally {
    Pop-Location
}

# ── Verify output ───────────────────────────────────────────────────────

Write-Host ""
Write-Host "[4/4] Verifying build output..." -ForegroundColor Yellow

$EngineExe = Join-Path (Join-Path (Join-Path $EngineDir "dist") "novem-engine") "novem-engine.exe"
if (-not (Test-Path $EngineExe)) {
    Write-Error "Engine executable not found at $EngineExe"
}

$DistPath = Join-Path (Join-Path $EngineDir "dist") "novem-engine"
$TotalSize = [math]::Round(((Get-ChildItem -Recurse $DistPath | Measure-Object -Property Length -Sum).Sum) / 1MB, 0)

Write-Host "  Output: $DistPath" -ForegroundColor White
Write-Host "  Size:   $TotalSize MB" -ForegroundColor White
Write-Host "  Exe:    $EngineExe" -ForegroundColor White

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Engine build complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
