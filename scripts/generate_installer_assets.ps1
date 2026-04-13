#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate NSIS installer branding images for NOVEM.

.DESCRIPTION
    Creates BMP images required by the NSIS installer:
      - Header image  (150×57)  — shown in the top-right of every page
      - Sidebar image (164×314) — shown on Welcome and Finish pages

    These are 24-bit BMPs with NOVEM branding (dark background, green accent).

.EXAMPLE
    .\scripts\generate_installer_assets.ps1
#>

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Drawing

$Root     = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$IconsDir = Join-Path (Join-Path (Join-Path $Root "desktop") "src-tauri") "icons"

Write-Host ""
Write-Host "Generating NSIS installer branding images..." -ForegroundColor Cyan

# ── Brand colours ───────────────────────────────────────────────────────
$BgColor       = [System.Drawing.Color]::FromArgb(14, 14, 14)         # #0e0e0e
$AccentColor   = [System.Drawing.Color]::FromArgb(82, 196, 26)        # #52c41a
$AccentDim     = [System.Drawing.Color]::FromArgb(40, 82, 196, 26)    # green 15%
$TextColor     = [System.Drawing.Color]::FromArgb(240, 240, 240)      # #f0f0f0
$TextMuted     = [System.Drawing.Color]::FromArgb(120, 255, 255, 255) # white 47%
$BorderColor   = [System.Drawing.Color]::FromArgb(25, 255, 255, 255)  # white 10%

# ── Fonts (system safe) ────────────────────────────────────────────────
$FontLarge  = New-Object System.Drawing.Font("Segoe UI", 14, [System.Drawing.FontStyle]::Bold)
$FontSmall  = New-Object System.Drawing.Font("Segoe UI", 7,  [System.Drawing.FontStyle]::Regular)
$FontTiny   = New-Object System.Drawing.Font("Segoe UI", 6,  [System.Drawing.FontStyle]::Regular)

# ── Helper: draw a subtle grid pattern ──────────────────────────────────
function Draw-Grid($g, $w, $h) {
    $pen = New-Object System.Drawing.Pen($BorderColor, 1)
    $step = 24
    for ($x = 0; $x -lt $w; $x += $step) { $g.DrawLine($pen, $x, 0, $x, $h) }
    for ($y = 0; $y -lt $h; $y += $step) { $g.DrawLine($pen, 0, $y, $w, $y) }
    $pen.Dispose()
}

# ═════════════════════════════════════════════════════════════════════════
# 1. SIDEBAR IMAGE (164 × 314)
# ═════════════════════════════════════════════════════════════════════════
$sw = 164; $sh = 314
$sidebar = New-Object System.Drawing.Bitmap($sw, $sh, [System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
$g = [System.Drawing.Graphics]::FromImage($sidebar)
$g.SmoothingMode     = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit

# Background
$g.Clear($BgColor)

# Subtle grid texture
Draw-Grid $g $sw $sh

# Green accent stripe at the top (3px)
$accentBrush = New-Object System.Drawing.SolidBrush($AccentColor)
$g.FillRectangle($accentBrush, 0, 0, $sw, 3)

# Green glow (radial-ish effect using layered ellipses)
for ($i = 5; $i -gt 0; $i--) {
    $alpha = [int](8 * $i)
    $glowBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb($alpha, 82, 196, 26))
    $size = 40 + ($i * 28)
    $x = ($sw - $size) / 2
    $y = 80 - ($size / 2)
    $g.FillEllipse($glowBrush, $x, $y, $size, $size)
    $glowBrush.Dispose()
}

# "NOVEM" text
$titleBrush = New-Object System.Drawing.SolidBrush($TextColor)
$titleFont  = New-Object System.Drawing.Font("Segoe UI", 18, [System.Drawing.FontStyle]::Bold)
$sf = New-Object System.Drawing.StringFormat
$sf.Alignment     = [System.Drawing.StringAlignment]::Center
$sf.LineAlignment = [System.Drawing.StringAlignment]::Center
$g.DrawString("NOVEM", $titleFont, $titleBrush, [System.Drawing.RectangleF]::new(0, 50, $sw, 50), $sf)

# Accent dot
$g.FillEllipse($accentBrush, ($sw / 2 - 3), 110, 6, 6)

# Descriptor text
$descBrush = New-Object System.Drawing.SolidBrush($TextMuted)
$descFont  = New-Object System.Drawing.Font("Segoe UI", 6.5, [System.Drawing.FontStyle]::Regular)
$g.DrawString("E-COMMERCE", $descFont, $descBrush, [System.Drawing.RectangleF]::new(0, 122, $sw, 16), $sf)
$g.DrawString("INTELLIGENCE", $descFont, $descBrush, [System.Drawing.RectangleF]::new(0, 136, $sw, 16), $sf)
$g.DrawString("PLATFORM", $descFont, $descBrush, [System.Drawing.RectangleF]::new(0, 150, $sw, 16), $sf)

# Version at bottom
$verBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(60, 255, 255, 255))
$verFont  = New-Object System.Drawing.Font("Segoe UI", 6, [System.Drawing.FontStyle]::Regular)
$g.DrawString("v1.0.0", $verFont, $verBrush, [System.Drawing.RectangleF]::new(0, $sh - 30, $sw, 20), $sf)

# Bottom accent stripe
$g.FillRectangle($accentBrush, 0, $sh - 3, $sw, 3)

# Save
$g.Dispose()
$sidebarPath = Join-Path $IconsDir "installer-sidebar.bmp"
$sidebar.Save($sidebarPath, [System.Drawing.Imaging.ImageFormat]::Bmp)
$sidebar.Dispose()
Write-Host "  Sidebar: $sidebarPath (164x314)" -ForegroundColor Green

# ═════════════════════════════════════════════════════════════════════════
# 2. HEADER IMAGE (150 × 57)
# ═════════════════════════════════════════════════════════════════════════
$hw = 150; $hh = 57
$header = New-Object System.Drawing.Bitmap($hw, $hh, [System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
$g = [System.Drawing.Graphics]::FromImage($header)
$g.SmoothingMode     = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit

# Background
$g.Clear($BgColor)

# Subtle grid
Draw-Grid $g $hw $hh

# Green accent line at left (2px)
$g.FillRectangle($accentBrush, 0, 0, 2, $hh)

# "NOVEM" text
$hTitleFont  = New-Object System.Drawing.Font("Segoe UI", 13, [System.Drawing.FontStyle]::Bold)
$hTitleBrush = New-Object System.Drawing.SolidBrush($TextColor)
$hsf = New-Object System.Drawing.StringFormat
$hsf.Alignment     = [System.Drawing.StringAlignment]::Center
$hsf.LineAlignment = [System.Drawing.StringAlignment]::Center
$g.DrawString("NOVEM", $hTitleFont, $hTitleBrush, [System.Drawing.RectangleF]::new(2, -2, $hw - 2, $hh), $hsf)

# Subtle descriptor below
$hDescFont = New-Object System.Drawing.Font("Segoe UI", 5.5, [System.Drawing.FontStyle]::Regular)
$g.DrawString("Intelligence Platform", $hDescFont, $descBrush, [System.Drawing.RectangleF]::new(2, 14, $hw - 2, $hh), $hsf)

# Save
$g.Dispose()
$headerPath = Join-Path $IconsDir "installer-header.bmp"
$header.Save($headerPath, [System.Drawing.Imaging.ImageFormat]::Bmp)
$header.Dispose()
Write-Host "  Header:  $headerPath (150x57)" -ForegroundColor Green

# ── Cleanup ─────────────────────────────────────────────────────────────
$titleFont.Dispose()
$FontLarge.Dispose()
$FontSmall.Dispose()
$FontTiny.Dispose()
$accentBrush.Dispose()
$titleBrush.Dispose()
$descBrush.Dispose()
$verBrush.Dispose()
$hTitleFont.Dispose()
$hTitleBrush.Dispose()
$hDescFont.Dispose()

Write-Host ""
Write-Host "  Installer assets generated." -ForegroundColor Cyan
Write-Host ""
