# KAWAL SIBER — Operational & Automation Scripts

## 1. Overview

This directory provides automated management and verification scripts for the KAWAL SIBER monorepo:

| Script | Runtime | Purpose |
| :--- | :--- | :--- |
| [`verify-sqlite-integrity.py`](./verify-sqlite-integrity.py) | Python 3.12 | Read-only structural database integrity and foreign-key check. |
| [`run-all-tests.ps1`](./run-all-tests.ps1) | PowerShell | Unified test runner: Backend pytest (129), Worker pytest (22), Acceptance (25), and Frontend type-check. |
| [`start-local-dev.ps1`](./start-local-dev.ps1) | PowerShell | Guidance and pre-flight verification for local loopback development. |
| [`setup-tools.ps1`](./setup-tools.ps1) | PowerShell | Clones and pins external Git dependencies (`deep-eye` and `scanner-website`). |

---

## 2. Usage Instructions

### Run Complete Test Suite
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run-all-tests.ps1
```

### Inspect Database Integrity (Zero Data Loss Check)
```powershell
python scripts/verify-sqlite-integrity.py
```
Outputs structural integrity status, foreign-key violation count, and record tallies across all 16 tables without acquiring exclusive write locks.
