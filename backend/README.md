# KAWAL SIBER — Backend API Component

## 1. Purpose & Architecture

The **KAWAL SIBER Backend** is the core API and business logic layer for territorial defense monitoring. Built on **FastAPI** and **SQLAlchemy 2.0**, it exposes RESTful endpoints for asset inventory, authorized network scanning, Suricata intrusion telemetry ingestion, incident correlation, AI triage runs, and cryptographic PDF/HTML/JSON report generation.

### Key Architecture Characteristics:
- **FastAPI Framework**: Asynchronous, high-throughput endpoints with OpenAPI 3.1 documentation (`/docs`, `/redoc`).
- **Database Portability**: Operates on SQLite with WAL journal mode and busy timeout for local Windows development; switches seamlessly to PostgreSQL 16 (Amazon RDS Multi-AZ or EC2 cluster) via `DATABASE_URL`.
- **Stateless Authentication**: JWT bearer tokens signed with HMAC-SHA256. Dual backend instances share the same secret key with zero in-memory session affinity required.
- **Alembic Database Migrations**: 8 sequential schema revisions (`0001` through `0008`) managing tables, indices, and audit chains.
- **Cryptographic Audit Log**: Append-only event chaining with SHA-256 genesis hashes and tampering detection for all generated reports.

---

## 2. Requirements & Dependencies

- **Python**: `3.12.x` (Verified with Python `3.12.10`).
- **Framework**: `FastAPI 0.115.5`, `Starlette 0.41.3`.
- **ASGI Server**: `Uvicorn 0.32.1`.
- **ORM & Migrations**: `SQLAlchemy 2.0.36`, `Alembic 1.14.0`.
- **Validation**: `Pydantic 2.10.2`.
- **Reporting Engine**: `ReportLab 4.2.5` (PDF generation), `Jinja2` (HTML generation).
- **Security**: `passlib[bcrypt]`, `python-jose[cryptography]`.

---

## 3. Installation & Virtual Environment

From the `kawal-siber` directory:

```bash
# Windows
python -m venv backend/.venv
backend\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r backend/requirements.txt

# Linux / macOS
python3.12 -m venv backend/.venv
source backend/.venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
```

---

## 4. Environment Configuration

Configuration is loaded from environment variables or `.env`:

```ini
# Local SQLite Database (Default)
DATABASE_URL=sqlite:///storage/kawal_siber.db

# Production PostgreSQL Database
# DATABASE_URL=postgresql://kawal_user:password@ks-db-01:5432/kawal_siber

# Security & Session
SECRET_KEY=KawalSiberDevelopmentSecretKey2026!
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Network & Host
FRONTEND_URL=http://127.0.0.1:3000
TOOLS_AGENT_URL=http://127.0.0.1:9000

# Connection Pool Sizing (PostgreSQL only)
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800

# Storage & Logging
PYTHONUNBUFFERED=1
```

---

## 5. Database Schema & Alembic Migrations

The database schema is managed via Alembic in `backend/alembic/`:

```bash
cd backend

# Apply all migrations to the latest HEAD (Revision 0008)
alembic upgrade head

# Inspect current schema revision
alembic current

# Show migration history
alembic history --verbose
```

### Alembic Revision Chain:
- `0001_initial_schema.py`: Assets, scan scopes, scan jobs, scan results.
- `0002_phase2_schema.py`: Suricata rules, events, and telemetry.
- `0003_phase3_schema.py`: Incidents and event correlation links.
- `0004_phase4_schema.py`: Web security targets, assessments, and findings.
- `0005_phase5_schema.py`: AI triage analysis runs and confidence scores.
- `0006_phase6_schema.py`: Automated report generation and metadata.
- `0007_phase6_addendum.py`: Enhanced report reproducibility and disclaimer fields.
- `0008_report_audit_events.py`: Append-only cryptographic audit trail with SHA-256 hash chaining.

---

## 6. Running the API Server

### Localhost Development Mode (Explicit Loopback):
```bash
# From kawal-siber/backend directory:
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Or from kawal-siber directory:
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

### Interactive API Documentation:
- **Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`
- **Health Check Endpoint**: `http://127.0.0.1:8000/api/v1/health`

---

## 7. Automated Testing Suite

The backend test suite contains **129 automated unit and integration tests** covering all modules:

```bash
# Run the entire backend test suite
pytest backend/tests -v

# Run specific functional tests
pytest backend/tests/test_assets.py -v
pytest backend/tests/test_database_integrity.py -v
pytest backend/tests/test_phase6_reporting.py -v
```

---

## 8. Docker Containerization

Built using a multi-stage `python:3.12-slim` image running as unprivileged user `appuser` (UID 1001):

```bash
# Build backend image
docker build -t kawal-siber-backend:latest -f backend/Dockerfile backend

# Run container
docker run -d \
  --name backend \
  -p 127.0.0.1:8000:8000 \
  -e DATABASE_URL=sqlite:////data/kawal_siber.db \
  kawal-siber-backend:latest
```
