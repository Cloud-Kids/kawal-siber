# ==============================================================================
# setup-tools.ps1 — Reproducible Security Tools Setup Script for KAWAL SIBER
# Clones and configures pinned external repositories (Deep Eye & Scanner-Website)
# without committing huge virtual environments or binary files into Git.
# ==============================================================================
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectDir = Split-Path -Parent $ScriptDir
$ToolsDir = Join-Path $ProjectDir "tools"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   KAWAL SIBER — EXTERNAL TOOLS SETUP (REPRODUCIBLE)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

if (-not (Test-Path $ToolsDir)) {
    New-Item -ItemType Directory -Path $ToolsDir | Out-Null
}

# 1. Setup Deep Eye
$DeepEyeDir = Join-Path $ToolsDir "deep-eye"
if (-not (Test-Path $DeepEyeDir)) {
    Write-Host "[1/2] Cloning Deep Eye (Pinned commit e4397d1)..." -ForegroundColor Yellow
    git clone https://github.com/zakirkun/deep-eye.git $DeepEyeDir
    Push-Location $DeepEyeDir
    try {
        git checkout e4397d1
        Write-Host "Deep Eye pinned to commit e4397d1." -ForegroundColor Green
    } finally {
        Pop-Location
    }
} else {
    Write-Host "[1/2] Deep Eye directory already exists at $DeepEyeDir." -ForegroundColor Green
}

# 2. Setup Scanner-Website
$ScannerDir = Join-Path $ToolsDir "scanner-website"
if (-not (Test-Path $ScannerDir)) {
    Write-Host "[2/2] Cloning Scanner-Website (Pinned commit 4a8c9c2)..." -ForegroundColor Yellow
    git clone https://github.com/kc0nk/Scanner-Website.git $ScannerDir
    Push-Location $ScannerDir
    try {
        git checkout 4a8c9c2
        Write-Host "Scanner-Website pinned to commit 4a8c9c2." -ForegroundColor Green
    } finally {
        Pop-Location
    }
} else {
    Write-Host "[2/2] Scanner-Website directory already exists at $ScannerDir." -ForegroundColor Green
}

Write-Host "`nExternal tools verified and ready." -ForegroundColor Green
