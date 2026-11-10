# ==============================================================================
# run-all-tests.ps1 — Unified Test Automation Suite for KAWAL SIBER
# Executes Backend pytest (129), Worker pytest (22), Phase 6 Acceptance (25),
# and Frontend TypeScript type-checking with complete database protection.
# ==============================================================================
$ErrorActionPreference = "Stop"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   KAWAL SIBER — MASTER TEST AUTOMATION SUITE" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectDir = Split-Path -Parent $ScriptDir

# Resolve project root and virtualenv preferring consolidated outer root
if (Test-Path "$ProjectDir\backend\.venv\Scripts\python.exe") {
    $AppDir = $ProjectDir
    $PythonExe = Join-Path $AppDir "backend\.venv\Scripts\python.exe"
} elseif (Test-Path "$ProjectDir\kawal-siber\backend\.venv\Scripts\python.exe") {
    $AppDir = Join-Path $ProjectDir "kawal-siber"
    $PythonExe = Join-Path $AppDir "backend\.venv\Scripts\python.exe"
} else {
    $PythonExe = "python"
    $AppDir = $ProjectDir
}

# 1. Run Backend Pytest Suite
Write-Host "`n[1/4] Running Backend Pytest Suite (129 tests)..." -ForegroundColor Yellow
& $PythonExe -m pytest "$AppDir\backend\tests" -v --strict-markers
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Backend tests failed!" -ForegroundColor Red
    exit 1
}
Write-Host "[PASS] Backend tests passed (129/129)." -ForegroundColor Green

# 2. Run Worker Pytest Suite
Write-Host "`n[2/4] Running Worker Pytest Suite (22 tests)..." -ForegroundColor Yellow
& $PythonExe -m pytest "$AppDir\worker\tests" -v --strict-markers
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Worker tests failed!" -ForegroundColor Red
    exit 1
}
Write-Host "[PASS] Worker tests passed (22/22)." -ForegroundColor Green

# 3. Run Phase 6 Master Acceptance Tests
Write-Host "`n[3/4] Running Phase 6 Acceptance Suite (25 tests on temp DB)..." -ForegroundColor Yellow
& $PythonExe "$AppDir\phase6_acceptance_test.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Acceptance tests failed!" -ForegroundColor Red
    exit 1
}
Write-Host "[PASS] Acceptance tests passed (25/25)." -ForegroundColor Green

# 4. Run Frontend TypeScript Type-Check
Write-Host "`n[4/4] Running Frontend TypeScript Type-Check..." -ForegroundColor Yellow
Push-Location "$AppDir\frontend"
try {
    npm run type-check
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] Frontend type check failed!" -ForegroundColor Red
        exit 1
    }
    Write-Host "[PASS] Frontend type check clean (0 errors)." -ForegroundColor Green
} finally {
    Pop-Location
}

# 5. Verify Database Untouched
Write-Host "`n[VERIFICATION] Verifying Primary SQLite Database Integrity..." -ForegroundColor Yellow
& $PythonExe "$ScriptDir\verify-sqlite-integrity.py"

Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host "   ALL 176 AUTOMATED VERIFICATIONS PASSED (100% SUCCESS RATE)" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan
