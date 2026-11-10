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

### Active Target: Single-Instance Linux Architecture (EC2 / Proxmox VM / LXC)
The primary and immediate deployment target runs all services on **one standalone Linux host** orchestrated by Docker Engine and Compose. Only the Nginx Reverse Proxy publishes ports (80/443); all application containers reside on an isolated internal bridge network (`kawal_net`):

```
                    ┌────────────────────────────────────────────────────────┐
                    │            STANDALONE LINUX HOST (UBUNTU 24.04)         │
                    │                                                        │
INTERNET / OPERATOR ──►│  [Host Firewall / AWS Security Group: 22, 80, 443]   │
                    │                                                        │
                    │  ┌──────────────────────────────────────────────────┐  │
                    │  │              DOCKER ENGINE COMPOSE               │  │
                    │  │                                                  │  │
                    │  │  ┌────────────────────────────────────────────┐  │  │
                    │  │  │  REVERSE PROXY (Nginx :80/:443)            │  │  │
                    │  │  └───────────────┬───────────────────┬────────┘  │  │
                    │  │                  │                   │           │  │
                    │  │     (internal)   ▼       (internal)  ▼           │  │
                    │  │   ┌─────────────────┐    ┌────────────────────┐  │  │
                    │  │   │ FRONTEND        │    │ BACKEND            │  │  │
                    │  │   │ Next.js 15 SSR  │    │ FastAPI REST API   │  │  │
                    │  │   │ (:3000 internal)│    │ (:8000 internal)   │  │  │
                    │  │   └─────────────────┘    └────────┬───────────┘  │  │
                    │  │                                   │              │  │
                    │  │                      (atomic queue/shared WAL)   │  │
                    │  │                                   │              │  │
                    │  │                          ┌────────▼───────────┐  │  │
                    │  │                          │ WORKER (Celery/Q)  │  │  │
                    │  │                          │ Nmap / Forensics   │  │  │
                    │  │                          └────────┬───────────┘  │  │
                    │  │                                   │              │  │
                    │  └───────────────────────────────────┼──────────────┘  │
                    │                                      │                 │
                    │       ┌──────────────────────────────▼──────────┐      │
                    │       │ HOST PERSISTENT STORAGE:                │      │
                    │       │ /opt/kawal-siber/storage/kawal_siber.db │      │
                    │       │ /opt/kawal-siber/storage/reports/       │      │
                    │       └─────────────────────────────────────────┘      │
                    └────────────────────────────────────────────────────────┘
```

> [!NOTE]
> Multi-host distributed EC2 redundancy and AWS ECS Multi-AZ architectures are preserved in [`deploy/aws-ec2/`](deploy/aws-ec2/) and [`docs/deployment/aws-ec2/`](docs/deployment/aws-ec2/) as **Future Enterprise Architecture / Extensions**.

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

## 8. Deployment Architecture (Active Single-Instance & Future Roadmap)

### 8.1 Primary Active Target: Single-Instance Linux Deployment
The immediate, fully self-contained deployment target for KAWAL SIBER is **ONE STANDALONE LINUX HOST** running Docker Engine and Docker Compose. This runs portably across:
- **Amazon EC2**: Ubuntu Server 24.04 LTS (`m7i.xlarge` recommended, 4 vCPU / 16 GiB RAM / 100 GB gp3).
- **Proxmox QEMU Virtual Machine**: Ubuntu Server 24.04 LTS (100% EC2 parity).
- **Proxmox Unprivileged LXC**: With `features: nesting=1,keyctl=1` and ext4 storage backend.

- **Canonical Runbook**: [`deploy/single-instance/README.md`](deploy/single-instance/README.md)
- **Docker Compose Manifest**: [`deploy/single-instance/compose.single-instance.yaml`](deploy/single-instance/compose.single-instance.yaml)
- **Nginx Ingress Configuration**: [`deploy/single-instance/nginx.conf`](deploy/single-instance/nginx.conf)

#### Standalone Stack Components:
1. **Reverse Proxy (Nginx 1.27)**: The only service with host port bindings (80/443). Enforces TLS termination, security headers (CSP, HSTS, X-Frame-Options), gzip compression, proxies `/api/v1/` to backend:8000, and routes UI traffic to frontend:3000.
2. **Frontend UI (Next.js 15.3)**: Standalone SSR server listening on port 3000 inside `kawal_net`. `API_INTERNAL_URL=http://backend:8000` is passed via build ARG and serialized into `.next/routes-manifest.json`.
3. **Backend API (FastAPI 0.115)**: Uvicorn ASGI server on port 8000 inside `kawal_net`. Connects to SQLite at `/data/kawal_siber.db`.
4. **Security Worker (Celery/Queue Daemon)**: Asynchronous background daemon claiming jobs atomically via SQLite transitions. Mounts `/data/kawal_siber.db` and `/data/reports`.
5. **Persistent Storage (Host Mount)**: SQLite database (`storage/kawal_siber.db`) in Write-Ahead Logging (WAL) mode and forensic reports (`storage/reports/`).

#### Strict Exclusion of Cloud Dependencies:
The single-instance target strictly excludes AWS managed application services:
- **NO Amazon ECS / ECR**: All container images are built locally on the host via Docker Compose.
- **NO Amazon RDS**: Persistence is provided by SQLite on host storage in WAL mode.
- **NO Amazon Application Load Balancer (ALB)**: Ingress routing and TLS are terminated by containerized Nginx.
- **NO AWS Secrets Manager / SSM**: Environment variables are loaded from host `.env` file (`chmod 600`).
- **NO AWS S3 / CloudWatch**: Persistent reports and logs reside on host storage with Docker json-file rotation.

### 8.2 Proxmox Portability (VM vs LXC)
- **Proxmox QEMU VM**: Recommended option. Full hardware virtualization with standard Linux kernel provides 100% behavioral parity with AWS EC2.
- **Proxmox Unprivileged LXC**: Requires `features: nesting=1,keyctl=1` in `/etc/pve/lxc/<CTID>.conf`. Must use ext4 storage driver to avoid overlayfs-on-ZFS performance penalties. Nmap scans execute in TCP connect mode (`-sT`) if raw packet capabilities are restricted.

### 8.3 Limitations of Single-Instance Architecture
- **Host-Level Single Point of Failure (SPOF)**: All components run on one machine. A host crash causes downtime until the instance recovers.
- **SQLite Concurrency Bound**: Well-suited for hackathon workloads, but high concurrent write volume (>100 RPS) requires upgrading to PostgreSQL.
- **Local Tool Sandboxing**: Nmap and Suricata execute inside containers sharing host CPU/memory resources.

### 8.4 Future Enterprise Roadmap (Levels 2 & 3)
For high-concurrency, multi-region, or military operational deployments, KAWAL SIBER maintains two advanced architectures:
- **Level 2: Distributed EC2 Container Redundancy**: 6 dedicated EC2 instances running 2 containers each (12 containers total) with PostgreSQL streaming replication. Runbook: [`deploy/aws-ec2/README.md`](deploy/aws-ec2/README.md).
- **Level 3: AWS ECS Multi-AZ Enterprise**: Automated GitHub Actions CI/CD deploying onto multi-AZ ECS on EC2 fronted by AWS ALB and Amazon RDS PostgreSQL Multi-AZ. Reference: [`docs/deployment/aws-ec2/15-CICD-ARCHITECTURE.md`](docs/deployment/aws-ec2/15-CICD-ARCHITECTURE.md) and [`infra/aws/`](infra/aws/).

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

- **[Single-Instance Production Deployment Runbook](deploy/single-instance/README.md)** ➔ *Active Primary Deployment Guide (EC2/Proxmox)*
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
