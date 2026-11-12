# KAWAL SIBER — Security Worker Daemon Component

## 1. Purpose & Responsibilities

The **KAWAL SIBER Security Worker** is a background daemon that handles asynchronous, long-running defense workflows decoupled from the user-facing API:
1. **Authorized Network Discovery & Port Scanning**: Claims `ScanJob` tasks, re-verifies target IP against active `ScanScope` CIDRs, executes Nmap, and parses XML results.
2. **Web Security Assessments**: Claims `WebAssessment` tasks and executes non-destructive passive/safe HTTP profiling.
3. **AI Triage Runs**: Claims `AITriageRun` tasks, generates prompt contexts from incidents, and invokes local/remote LLMs with graceful rule-based fallback.
4. **Automated Security Report Generation**: Compiles multi-period data snapshots, enforces formula injection sanitization, generates signed PDF/HTML/JSON reports, and registers SHA-256 audit events.
5. **Stale Job Reclamation**: Automatically detects and resets jobs stuck in `RUNNING` status if a worker process crashes mid-execution.

---

## 2. Requirements & Dependencies

- **Python**: `3.12.x` (Verified with Python `3.12.10`).
- **Nmap**: `7.95` or higher installed on system PATH.
- **Dependencies**: Listed in `worker/requirements.txt` (SQLAlchemy 2.0, ReportLab, Jinja2, httpx).
- **Permissions**: Runs as unprivileged user `worker` (UID 1001) in Docker; performs unprivileged TCP connect scans (`-sT`).

---

## 3. Installation

From the `kawal-siber` directory:

```bash
# Uses the same Python 3.12 virtualenv as backend, or a dedicated worker venv:
pip install -r worker/requirements.txt
```

---

## 4. Concurrency & Queue Mechanism

### Single Worker (Local SQLite Development):
- SQLite database transactions acquire short-lived table locks.
- `queue.py` uses `PRAGMA busy_timeout=10000` to prevent locked database errors.
- Atomic state transitions: `PENDING` -> `RUNNING` -> `COMPLETED` / `FAILED`.

### Concurrent Claiming (SQLite and PostgreSQL):
- SQLite has no ``SELECT ... FOR UPDATE SKIP LOCKED``. Claims use a single
  atomic conditional ``UPDATE ... WHERE status='PENDING' RETURNING`` so two
  consumers can never claim the same job (verified by
  ``worker/tests/test_queue_concurrency.py``).
- PostgreSQL keeps the ``SELECT ... FOR UPDATE`` row-lock path.
- Safe for multiple workers; for the single-instance deployment keep
  worker concurrency at 1 until load testing justifies more.

---

## 5. Running the Worker Daemon

### Local Development:
```bash
# Set environment variables if needed
export DATABASE_URL=sqlite:///storage/kawal_siber.db
export SCAN_ENABLED=true
export POLL_INTERVAL_SECONDS=2.0

# Start worker loop
python -m worker.main
```

### Heartbeat & Graceful Shutdown:
- The worker updates a local timestamp file `/tmp/worker_heartbeat` on every polling cycle.
- Traps `SIGINT` (Ctrl+C) and `SIGTERM` to allow in-flight tasks to complete or commit rollback before exiting cleanly.

---

## 6. Stale Job Recovery & Fault Tolerance

If a worker container terminates unexpectedly (e.g. host reboot or OOM kill):
- Tasks remain in `RUNNING` status with recorded `started_at` timestamps.
- Sibling worker processes periodically execute:
  - `recover_stale_running_scans(db, timeout_minutes=10)`
  - `recover_stale_running_reports(db, timeout_minutes=10)`
- Stale jobs are atomically transitioned back to `PENDING` with an explanatory recovery message and re-queued automatically.

---

## 7. Automated Testing Suite

The worker test suite contains **22 automated unit and reliability tests**:

```bash
# Run all worker tests
pytest worker/tests -v

# Run reliability & stale recovery tests
pytest worker/tests/test_report_worker_reliability.py -v
pytest worker/tests/test_scope_validator.py -v
pytest worker/tests/test_queue.py -v
```

---

## 8. Docker Containerization

```bash
# Build worker image (context is kawal-siber root)
docker build -t kawal-siber-worker:latest -f worker/Dockerfile .

# Run container
docker run -d \
  --name worker \
  -e DATABASE_URL=sqlite:////data/kawal_siber.db \
  -e SCAN_ENABLED=true \
  kawal-siber-worker:latest
```
