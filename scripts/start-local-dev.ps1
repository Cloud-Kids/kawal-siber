# ==============================================================================
# start-local-dev.ps1 — Local Development Startup Script for KAWAL SIBER
# Launches Backend (8000), Frontend (3000), and Worker Daemon on Windows Loopback
# ==============================================================================
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectDir = Split-Path -Parent $ScriptDir
$PythonExe = Join-Path $ProjectDir "backend\.venv\Scripts\python.exe"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   KAWAL SIBER — LOCAL DEVELOPMENT ENVIRONMENT STARTUP" -ForegroundColor Cyan
Write-Host "   Binding: 127.0.0.1 (Strict Loopback Isolation)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# Check database
Write-Host "[1/3] Verifying database integrity..." -ForegroundColor Yellow
& $PythonExe "$ScriptDir\verify-sqlite-integrity.py"

Write-Host "`nTo run the full stack locally in separate terminals:" -ForegroundColor White
Write-Host "  Terminal 1 (Backend API):" -ForegroundColor Cyan
Write-Host "    cd kawal-siber\backend"
Write-Host "    ..\backend\.venv\Scripts\Activate.ps1"
Write-Host "    uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

Write-Host "`n  Terminal 2 (Frontend UI):" -ForegroundColor Cyan
Write-Host "    cd kawal-siber\frontend"
Write-Host "    npm run dev"

Write-Host "`n  Terminal 3 (Worker Daemon):" -ForegroundColor Cyan
Write-Host "    cd kawal-siber"
Write-Host "    backend\.venv\Scripts\Activate.ps1"
Write-Host "    python -m worker.main"

Write-Host "`n======================================================================" -ForegroundColor Cyan
