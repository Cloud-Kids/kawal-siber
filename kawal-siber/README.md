# KAWAL SIBER — Sistem Pertahanan Siber Teritorial

[![Kartika Cyber Hackathon 2026](https://img.shields.io/badge/Event-Kartika_Cyber_Hackathon_2026-green.svg)](https://github.com/Cloud-Kids/kawal-siber)
[![Python 3.12](https://img.shields.io/badge/Python-3.12.10-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI_0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js 15](https://img.shields.io/badge/Frontend-Next.js_15.3-black.svg)](https://nextjs.org/)
[![PostgreSQL 16](https://img.shields.io/badge/Database-PostgreSQL_16_|_SQLite_WAL-336791.svg)](https://www.postgresql.org/)
[![Suricata IDS](https://img.shields.io/badge/IDS-Suricata_7.0-red.svg)](https://suricata.io/)
[![Automated Tests](https://img.shields.io/badge/Tests-176%2F176_PASS_(100%25)-brightgreen.svg)](#7-testing--quality-assurance)
[![Deployment Readiness](https://img.shields.io/badge/Readiness-NOT_PRODUCTION--READY-orange.svg)](#10-security-disclaimer--readiness-status)

**KAWAL SIBER** is a specialized territorial cybersecurity monitoring and defensive operations platform engineered for the **Kartika Cyber Hackathon 2026**. Designed to protect critical infrastructure and regional network assets, KAWAL SIBER combines automated asset discovery, real-time intrusion detection (Suricata), threat correlation, local AI incident triage, and tamper-evident cryptographic security reporting into a single unified monorepo.

---

## 1. Project Goals & Defensive Mission

- **Territorial Asset Visibility**: Continuously monitor, categorize, and track operational availability of vital regional IP assets.
- **Strict Scope Boundaries**: Enforce non-destructive discovery and auditing confined strictly to legally authorized CIDR blocks.
- **Intrusion Detection Telemetry**: Ingest, parse, and correlate Suricata network security monitoring (NSM) alerts and raw PCAP captures.
- **Deterministic Incident Intelligence**: Group disparate security events into actionable Incidents with causal timeline reconstruction.
- **Hybrid AI Triage Engine**: Augment human operators with contextual analysis and remediation plans, backed by an offline rule-based fallback.
- **Cryptographic Auditability**: Generate verifiable multi-format security reports protected by append-only SHA-256 hash chains.

---

## 2. Key Platform Features

| Capability | Module | Description |
| :--- | :--- | :--- |
| **Asset Discovery** | `worker/nmap_scanner.py` | Non-intrusive TCP connect discovery within authorized network scopes. |
| **Network Security Monitoring**| `backend/app/api/routes/monitoring.py` | EVE JSON parser, signature management, and PCAP header analysis. |
| **Incident Correlation** | `backend/app/services/` | Correlates IDS alerts with asset metadata to track repeated attacks. |
| **Web Application Security** | `tools/deep-eye` | Non-destructive passive/safe HTTP profiling with safe file-upload stubs. |
| **AI Incident Triage** | `worker/main.py` & `models.py` | Prompt injection defenses, credential redaction, and severity scoring. |
| **Automated Reporting** | `backend/app/reporting/` | Generates tamper-evident PDF, standalone HTML, and JSON reports. |
| **Audit Chaining** | `backend/app/models.py` | Cryptographic SHA-256 blockchain-style event log detecting retroactive tampering. |

---

## 3. Architecture & Monorepo Topology

KAWAL SIBER is organized as a single, cohesive **Monorepo** ensuring synchronization across schemas, background workers, tool integrations, and user interfaces.

```
                              PUBLIC INTERNET / OPERATORS
                                           │
                            [ AWS Application Load Balancer ]
                              (Multi-AZ Ingress & TLS ACM)
                                           │
                   ┌───────────────────────┴───────────────────────┐
                   │ Path: /api/*                                  │ Default: /*
                   ▼                                               ▼
      [ Backend ECS Cluster ]                         [ Frontend ECS Cluster ]
      - desiredCount = 2                              - desiredCount = 2
      - FastAPI (Port 8000)                           - Next.js 15 Standalone (3000)
      - Stateless JWT verification                    - 22 Pre-compiled routes
      - Connection Pool (20 + 10)                     - Synchronized static assets
                   │                                               │
                   ├───────────────────────┬───────────────────────┘
                   │ SQL Connection Pool   │ Internal REST (X-Agent-Key)
                   ▼                       ▼
      [ Amazon RDS PostgreSQL ]       [ Security Tools Agent ]
      - Multi-AZ High Availability    - desiredCount = 2 (Port 9000)
      - Physical Streaming Replica    - In-container CIDR scope guard
      - Automated Daily Backups       - Nmap 7.95, Suricata 7, Deep Eye
                   ▲                       ▲
                   │ SKIP LOCKED Queue     │ Subprocess Scans
                   └───────────────────────┤
                              [ Worker ECS Pool ]
                              - desiredCount = 2 (Async Daemons)
                              - Atomic Job Claim (FOR UPDATE SKIP LOCKED)
                              - Heartbeat & Stale Job Recovery (10m)
```

---

## 4. Technology Stack

| Layer | Component | Technologies & Versions |
| :--- | :--- | :--- |
| **Frontend** | UI & Dashboard | Next.js 15.3.3, React 19.1.0, TypeScript 5.6.3, Tailwind CSS, Lucide Icons |
| **Backend API** | REST API & Reporting | Python 3.12.10, FastAPI 0.115.5, SQLAlchemy 2.0.36, Pydantic 2.10, ReportLab 4.2 |
| **Database** | Persistence & ORM | PostgreSQL 16 (Production) / SQLite WAL Mode (Local Development), Alembic 1.14 |
| **Worker** | Background Processing | Python 3.12 Daemon, Asyncio, PostgreSQL SKIP LOCKED, Safe Subprocess Runner |
| **Security Tools** | Network & App Auditing| Nmap 7.95, Suricata 7.0.7, Deep Eye 1.4.0 (Hanzou) with non-destructive patch |
| **Orchestration** | Containers & Cloud | AWS ECS on EC2 (Multi-AZ), Amazon ECR, AWS Application Load Balancer, Docker |
| **CI / CD** | Automated Pipelines | GitHub Actions, AWS OIDC (No Static Keys), Trivy, Gitleaks, Pip-Audit |

---

## 5. Monorepo Directory Structure

```
.
├── .github/workflows/          # GitHub Actions CI/CD workflows
│   ├── ci.yml                  # Pull request & push quality gate (176 tests)
│   ├── deploy-production.yml   # OIDC ECR push, DB migration task & ECS rolling update
│   ├── rollback-production.yml # Operator-controlled manual rollback workflow
│   └── security-scan.yml       # Scheduled Trivy, Gitleaks, pip-audit & npm audit
├── backend/                    # FastAPI REST API, Alembic migrations & reporting
│   └── README.md               # ➔ Backend Component Documentation
├── frontend/                   # Next.js 15 App Router web application
│   └── README.md               # ➔ Frontend Component Documentation
├── worker/                     # Async background consumer daemon (SKIP LOCKED)
│   └── README.md               # ➔ Worker Daemon Documentation
├── tools/                      # Security tool execution layer & integration engines
│   ├── deep-eye/               # Deep Eye web scanner (Pinned commit e4397d1 with local patch)
│   ├── scanner-website/        # Web inspection toolkit (Pinned commit 4a8c9c2)
│   └── README.md               # ➔ Security Tools & Scope Guard Documentation
├── deploy/                     # Infrastructure deployment specifications
│   ├── aws/                    # Per-host Docker Compose configurations & scripts
│   ├── aws-ec2/                # AWS EC2 container redundancy & failover runbook
│   │   └── README.md           # ➔ AWS EC2 Redundancy Runbook
│   └── README.md               # ➔ General Deployment Guide
├── docs/                       # Architecture specifications & Phase reports
│   ├── deployment/aws-ec2/     # AWS ECS & CI/CD deployment documentation guides (15-21)
│   ├── reports/                # Phase 1 through 6 hardening & audit records
│   └── README.md               # ➔ Documentation Index & Test Metrics
├── infra/aws/                  # AWS Infrastructure as Code (IaC) configuration templates
│   ├── alb/                    # Multi-AZ ALB & target group routing rules
│   ├── cloudwatch/             # Production alarms & deployment metrics
│   ├── ecr/                    # Immutable ECR repository specifications
│   ├── ecs/                    # ECS Task Definitions & Multi-AZ Service specs
│   ├── iam/                    # OIDC trust policies & least-privilege IAM roles
│   └── rds/                    # Amazon RDS PostgreSQL Multi-AZ specifications
├── scripts/                    # Automation, test runners & verification utilities
│   ├── run-all-tests.ps1       # Master test automation runner (176 tests)
│   ├── start-local-dev.ps1     # Local development startup guide
│   ├── verify-sqlite-integrity.py # Read-only database integrity validator
│   ├── setup-tools.ps1         # Reproducible external tools setup script
│   └── README.md               # ➔ Scripts Documentation
├── storage/                    # [GITIGNORED] Local development runtime storage
│   ├── kawal_siber.db          # Operational SQLite database (Strictly preserved)
│   ├── reports/                # Generated PDF, HTML, JSON, CSV reports
│   └── suricata/               # Suricata configuration and rule templates
├── .dockerignore               # Multi-stage Docker context exclusion rules
├── .gitignore                  # Git ignore rules protecting local DB and secrets
├── compose.yaml                # Local 3-service Docker Compose evaluation stack
└── README.md                   # Master Repository Documentation (This file)
```

---

## 6. Local Development Quickstart

### Prerequisites
- Python `3.12.x` and Node.js `20.x` or `22.x LTS`.
- Git and Nmap `7.95` installed on PATH.

### Step 1: Clone the Repository
```bash
git clone https://github.com/Cloud-Kids/kawal-siber.git
cd kawal-siber
```

### Step 2: Backend Setup
```bash
cd backend
python -m venv .venv

# Windows:
.venv\Scripts\Activate.ps1
# Linux / macOS:
# source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
alembic upgrade head
```

### Step 3: Frontend Setup
```bash
cd ../frontend
npm ci
```

### Step 4: Launch Local Development Services
All local services bind strictly to `127.0.0.1` (loopback) to prevent accidental network exposure:
- **Terminal 1 (Backend API)**:
  ```bash
  cd backend
  uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
  ```
- **Terminal 2 (Frontend UI)**:
  ```bash
  cd frontend
  npm run dev
  ```
- **Terminal 3 (Worker Daemon)**:
  ```bash
  python -m worker.main
  ```

Access the application dashboard at `http://127.0.0.1:3000` and API documentation at `http://127.0.0.1:8000/docs`.

---

## 7. Testing & Quality Assurance

KAWAL SIBER maintains an exhaustive automated testing suite with **100% Pass Rate** across all executed test suites:

```bash
# Execute master test suite (runs all 176 automated verifications)
powershell -ExecutionPolicy Bypass -File scripts/run-all-tests.ps1
```

### Test Suite Breakdown:
1. **Backend Pytest Suite** (`pytest backend/tests -v`): **129/129 PASS** (100.26s)
2. **Worker Pytest Suite** (`pytest worker/tests -v`): **22/22 PASS** (29.42s)
3. **Phase 6 Master Acceptance Suite** (`python phase6_acceptance_test.py`): **25/25 PASS** (Executed on an isolated temporary database).
4. **Frontend TypeScript Compilation** (`npm run type-check`): **0 Errors**.
5. **Next.js Standalone Build** (`npm run build`): **22 User Routes Compiled Cleanly**.
6. **Database Integrity Verification** (`python scripts/verify-sqlite-integrity.py`): Primary database `storage/kawal_siber.db` strictly verified untouched (**356,352 bytes**, 0 FK violations).

---

## 8. AWS Production Deployment & CI/CD

### Architecture Overview
For production defense operations, KAWAL SIBER deploys onto **AWS ECS on EC2 across at least two Availability Zones (`ap-southeast-1a` and `ap-southeast-1b`)** backed by **Amazon RDS PostgreSQL Multi-AZ**:

- **GitHub Actions OIDC**: Authenticates builds to AWS IAM without static, long-lived access keys.
- **Amazon ECR Immutability**: All release images are tagged with the Git commit SHA (`sha-<short_sha>`) and scanned for vulnerabilities upon push.
- **Dedicated Database Migration Task**: Alembic migrations run once as a standalone ECS task before application services undergo rolling updates.
- **Automated Rollback Circuit Breaker**: If a new container revision fails health checks, ECS automatically rolls back to the previous stable revision.
- **Operator-Controlled Rollback**: Triggerable manually via [`.github/workflows/rollback-production.yml`](./.github/workflows/rollback-production.yml).

Detailed cloud deployment and setup documentation is located in [`docs/deployment/aws-ec2/`](./docs/deployment/aws-ec2/).

---

## 9. Security Notice & Defensive Scope Guardrails

> [!IMPORTANT]
> **DEFENSIVE OPERATIONAL RULES**
> 1. **Authorized Targets Only**: Port scanning and security auditing must be performed **only** against assets within legally authorized scan scopes (`ScanScope`).
> 2. **In-Container Scope Guard**: The tools execution layer unconditionally blocks scanning of loopback interfaces (`127.0.0.0/8`), AWS link-local metadata endpoints (`169.254.169.254`), and multicast addresses (`224.0.0.0/4`).
> 3. **Non-Destructive Testing**: All active vulnerability probing modules (e.g. destructive shell uploads) are stubbed or bypassed in compliance with hackathon safety mandates.
> 4. **No Plaintext Secrets**: Secrets must never be committed to source code or container images. Use AWS Secrets Manager or local `.env` files (excluded by `.gitignore`).

---

## 10. Security Disclaimer & Readiness Status

> [!CAUTION]
> **OFFICIAL READINESS STATUS: `NOT PRODUCTION-READY FOR THE PUBLIC INTERNET`**
> KAWAL SIBER has achieved a **100% automated test pass rate** in local and staging environments. However, before public internet exposure or military operational cutover, the following mandatory controls must be completed:
> - Full Amazon RDS Multi-AZ provisioning and production data cutover.
> - Private PKI mutual TLS (mTLS) certificate deployment between Backend and Tools Agent microservices.
> - AWS Web Application Firewall (AWS WAF) rule deployment protecting public ALB endpoints.
> - Formal third-party penetration testing and source code security review.

---

## 11. Component Documentation Links

- **[Frontend Web Application (Next.js 15)](frontend/README.md)**
- **[Backend API & Reporting Engine (FastAPI)](backend/README.md)**
- **[Security Worker Daemon (Async Queue)](worker/README.md)**
- **[Security Tools & Scope Guards (Nmap, Suricata, Deep Eye)](tools/README.md)**
- **[General Deployment Architecture](deploy/README.md)**
- **[AWS EC2 Distributed Redundancy Runbook](deploy/aws-ec2/README.md)**
- **[Technical Documentation & Engineering Archive](docs/README.md)**
- **[Operational & Verification Scripts](scripts/README.md)**

---

**KAWAL SIBER — Kartika Cyber Hackathon 2026**
*Sistem Pertahanan Siber Teritorial. Hak Cipta Dilindungi Undang-Undang.*
