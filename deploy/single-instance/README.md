# KAWAL SIBER — SINGLE-INSTANCE PRODUCTION DEPLOYMENT RUNBOOK
**Sistem Pertahanan Siber Teritorial — Kartika Cyber Hackathon 2026**  
**Document Version:** 1.0.0 (Production Single-Host Baseline)  
**Target Environment:** Standalone Linux Host (Amazon EC2 Ubuntu 24.04 LTS / Proxmox VM / LXC)  
**Ingress Architecture:** Single Public Reverse Proxy (Nginx) → Isolated Internal Containers  

---

## 1. Executive Summary & Architecture Overview

This runbook provides the definitive, end-to-end installation and operational procedure for deploying **KAWAL SIBER** onto a **single, standalone Linux host** using Docker Engine and Docker Compose.

```
                    ┌────────────────────────────────────────────────────────┐
                    │            STANDALONE LINUX HOST (UBUNTU 24.04)         │
                    │                                                        │
INTERNET / ADMIN ──►│  [Security Group / UFW: Allow 22, 80, 443 only]       │
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

### Core Architecture Invariants
1. **Single-Host Isolation**: All microservices run on one physical or virtual host. There is zero dependency on AWS managed multi-node application services (no ECS, ECR, RDS, ALB, S3, or Secrets Manager).
2. **Reverse Proxy Ingress**: Nginx is the only service that publishes ports (80/443) on the host. Frontend (:3000) and Backend (:8000) are attached strictly to the internal bridge network (`kawal_net`) with no host port bindings.
3. **Persistent SQLite Database**: The primary SQLite database (`kawal_siber.db`) and forensic reports are stored on the host filesystem and mounted into containers. SQLite Write-Ahead Logging (WAL) processes execute strictly on the same physical kernel. Network filesystems (NFS, EFS) are **strictly forbidden** for SQLite WAL.
4. **Deterministic Pinned Tooling**: Deep Eye (`e4397d1`) and Scanner-Website (`4a8c9c2`) are pinned as Git submodules. Deep Eye's local non-destructive safety patch in `modules/file_upload/upload_tester.py` is permanently preserved.
5. **No Blind External Dependencies**: Ollama AI is optional and disabled by default; the built-in deterministic `RuleBasedProvider` handles all triage without external GPU or cloud dependencies. Redis is not required (worker queue is 100% SQLite-backed).

---

## 2. Pre-Built EC2 Specification

| Parameter | Recommended Specification | Alternative Budget Test Specification |
| :--- | :--- | :--- |
| **Cloud Provider** | Amazon Web Services (AWS) EC2 | Amazon Web Services (AWS) EC2 |
| **Operating System** | Ubuntu Server 24.04 LTS (Noble Numbat) | Ubuntu Server 24.04 LTS (Noble Numbat) |
| **Architecture** | 64-bit (x86_64 / AMD64) | 64-bit (x86_64 / AMD64) |
| **Instance Type** | **`m7i.xlarge`** (General Purpose 7th Gen Intel) | **`t3.xlarge`** (Burstable 3rd Gen Intel) |
| **vCPU** | 4 vCPUs | 4 vCPUs |
| **Memory (RAM)** | 16 GiB | 16 GiB |
| **Root Volume** | 100 GiB gp3 SSD, Encrypted (KMS default) | 100 GiB gp3 SSD, Encrypted (KMS default) |
| **IOPS / Throughput**| 3,000 IOPS / 125 MB/s baseline | 3,000 IOPS / 125 MB/s baseline |
| **Performance Model**| Dedicated continuous compute | Burstable CPU credits (24 credits/hr). *Warning: In `unlimited` mode, sustained high CPU loads (e.g. concurrent Nmap scans) incur surplus credit surcharges.* |
| **Estimated Cost** | ~$0.2016 / hour (~$147 / month) | ~$0.1664 / hour (~$121 / month) |

> [!NOTE]
> Instance pricing and availability vary by AWS Region (e.g., `ap-southeast-1` Singapore or `us-east-1` N. Virginia). Reserved instances or Savings Plans reduce costs by up to 40% for long-term deployments.

---

## 3. Network, Security Group & Firewall Rules

### AWS EC2 Inbound Rules (Security Group: `sg-kawal-siber-prod`)

| Type | Protocol | Port Range | Source | Justification |
| :--- | :--- | :--- | :--- | :--- |
| **SSH** | TCP | `22` | `ADMIN_PUBLIC_IP/32` | Administrative shell access. **Never open to `0.0.0.0/0`**. |
| **HTTP** | TCP | `80` | `ADMIN_PUBLIC_IP/32` *(staging)* or `0.0.0.0/0` *(public)* | Public ingress; redirects to HTTPS in production. |
| **HTTPS**| TCP | `443` | `ADMIN_PUBLIC_IP/32` *(staging)* or `0.0.0.0/0` *(public)* | Encrypted TLS application access. |

### Blocked Ports (STRICT SECURITY BOUNDARY)
The following ports must **NEVER** be opened in AWS Security Groups or published on the host interface:
- **Port 3000** (Next.js Frontend) — Internal container access only.
- **Port 8000** (FastAPI Backend) — Internal container access only.
- **Port 11434** (Ollama AI) — Local loopback only.
- **Port 6379** (Redis) — Not used in single-host mode.

### Host Firewall (UFW) Configuration
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow proto tcp from YOUR_ADMIN_IP to any port 22 comment 'Admin SSH'
sudo ufw allow 80/tcp comment 'Nginx HTTP'
sudo ufw allow 443/tcp comment 'Nginx HTTPS'
sudo ufw enable
sudo ufw status verbose
```

---

## 4. Ubuntu Server Preparation & Docker Installation

Execute the following steps upon initial SSH login:

```bash
# 1. Verify operating system and architecture
lsb_release -a
uname -m
# Expected: Ubuntu 24.04 LTS, x86_64

# 2. Update apt package index and upgrade packages
sudo apt-get update && sudo apt-get upgrade -y

# 3. Set server timezone to UTC
sudo timedatectl set-timezone UTC

# 4. Install essential utilities
sudo apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    git \
    htop \
    jq \
    ufw \
    unzip

# 5. Install official Docker Engine repository
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 6. Install Docker Engine, CLI, and Docker Compose Plugin
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 7. Enable and verify Docker daemon
sudo systemctl enable --now docker
sudo docker version
sudo docker compose version

# 8. Test Docker container execution
sudo docker run --rm hello-world

# 9. Create dedicated deployment user & directory
sudo useradd -m -s /bin/bash deployer
sudo usermod -aG docker deployer
sudo mkdir -p /opt/kawal-siber
sudo chown -R deployer:deployer /opt/kawal-siber
```

---

## 5. Clone and Prepare Project

Log in as the `deployer` user:

```bash
sudo su - deployer
cd /opt/kawal-siber

# 1. Clone repository
git clone https://github.com/Cloud-Kids/kawal-siber.git .

# 2. Initialize and pin submodules
git submodule update --init --recursive
git submodule status
# Expected output:
# -e4397d17fcd6820489f36e0ed52f120d8a6b0c3d tools/deep-eye
# -4a8c9c2177cff77a19f0a61beda9484302473326 tools/scanner-website

# 3. Verify working tree is clean
git status

# 4. Prepare storage directories on host
mkdir -p storage/reports storage/pcaps storage/suricata storage/backups
chmod 750 storage
chmod 777 storage/reports  # Allow containerized backend and worker to write reports

# 5. Configure environment variables
cp .env.example .env
chmod 600 .env
```

---

## 6. Environment Variable Inventory

| Variable Name | Purpose | Required? | Safe Example / Default | Consumed By | Evaluation Scope |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`DATABASE_URL`** | SQLite database path connection string | **Yes** | `sqlite:////data/kawal_siber.db` | Backend & Worker | Runtime |
| **`API_INTERNAL_URL`** | Internal backend service URL for Next.js API proxy | **Yes** | `http://backend:8000` | Frontend | **Build-time & Runtime** |
| **`FRONTEND_URL`** | Backend CORS origin allowlist | **Yes** | `http://frontend:3000` | Backend | Runtime |
| **`NODE_ENV`** | Node.js execution mode | **Yes** | `production` | Frontend | Build & Runtime |
| **`PORT`** | Internal HTTP listening port for Next.js | No | `3000` | Frontend | Runtime |
| **`HOSTNAME`** | Network interface binding inside container | **Yes** | `0.0.0.0` | Frontend | Runtime |
| **`NEXT_TELEMETRY_DISABLED`** | Opt-out of Next.js telemetry | No | `1` | Frontend | Build & Runtime |
| **`SCAN_ENABLED`** | Safety kill-switch for automated network scans | **Yes** | `true` *(or `false` for passive)* | Worker | Runtime |
| **`NMAP_TIMEOUT_SECONDS`** | Maximum execution time per Nmap job | No | `60` | Worker | Runtime |
| **`POLL_INTERVAL_SECONDS`** | Polling frequency for queue claim loop | No | `3.0` | Worker | Runtime |
| **`AI_ENABLED`** | Enable AI triage engine | No | `true` | Backend | Runtime |
| **`AI_PROVIDER`** | AI Provider selection (`auto`, `ollama`, `rule_based`)| No | `auto` *(falls back to rule_based)* | Backend | Runtime |
| **`OLLAMA_BASE_URL`** | Ollama API endpoint (if deployed) | No | `http://localhost:11434` | Backend | Runtime |

> [!CRITICAL]
> **NEXT.JS BUILD-TIME SERIALIZATION**:
> In Next.js 15, `next.config.ts` rewrites are evaluated and baked into `.next/routes-manifest.json` during `next build`. Therefore, `API_INTERNAL_URL=http://backend:8000` **must be present during the Docker image build** via `ARG API_INTERNAL_URL`. Setting it solely at runtime will **not** update the pre-compiled routes manifest.

---

## 7. Ordered 18-Step Deployment Runbook

### STEP 1: Launch EC2 Instance
- **Action**: AWS Console or CLI: launch `Ubuntu 24.04 LTS`, `m7i.xlarge`, 100 GB gp3 encrypted.

### STEP 2: Configure Network & Security Group
- **Action**: Attach `sg-kawal-siber-prod`. Inbound: SSH (22), HTTP (80), HTTPS (443) from your IP.

### STEP 3: Connect via SSH
```bash
ssh -i /path/to/key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

### STEP 4: Server Preparation & Docker Installation
```bash
# Execute preparation commands from Section 4 of this runbook
```

### STEP 5: Clone Repository as Deployer User
```bash
sudo su - deployer
cd /opt/kawal-siber && git clone https://github.com/Cloud-Kids/kawal-siber.git .
git submodule update --init --recursive
```

### STEP 6: Configure Environment
```bash
cp .env.example .env
nano .env # Set appropriate values (verify DATABASE_URL=sqlite:////data/kawal_siber.db)
```

### STEP 7: Prepare Persistent Storage
```bash
mkdir -p storage/reports storage/pcaps storage/suricata
# If migrating existing operational database, copy it here:
# cp /backup/kawal_siber.db storage/kawal_siber.db
```

### STEP 8: Validate Compose Configuration
```bash
docker compose -f deploy/single-instance/compose.single-instance.yaml config
# Expected output: Full resolved YAML without errors.
```

### STEP 9: Build Container Images
```bash
docker compose -f deploy/single-instance/compose.single-instance.yaml build
# Expected: Successful build of backend, worker, frontend images.
```

### STEP 10: Initialize Database Migrations
```bash
docker compose -f deploy/single-instance/compose.single-instance.yaml run --rm backend alembic upgrade head
# Expected output:
# INFO  [alembic.runtime.migration] Running upgrade  -> 0001_initial_schema
# ...
# INFO  [alembic.runtime.migration] Running upgrade 0007 -> 0008_report_audit_events
```

### STEP 11: Start Services in Detached Mode
```bash
docker compose -f deploy/single-instance/compose.single-instance.yaml up -d
```

### STEP 12: Inspect Container Status
```bash
docker compose -f deploy/single-instance/compose.single-instance.yaml ps
# Expected output:
# NAME                   IMAGE                    STATUS
# kawal-siber-backend    kawal-siber-backend      Up (healthy)
# kawal-siber-frontend   kawal-siber-frontend     Up (healthy)
# kawal-siber-proxy      nginx:1.27-alpine        Up (healthy)
# kawal-siber-worker     kawal-siber-worker       Up (healthy)
```

### STEP 13: Inspect Application Logs
```bash
docker compose -f deploy/single-instance/compose.single-instance.yaml logs --tail=50 -f
# Verify zero unhandled exceptions.
```

### STEP 14: Verify Internal Service Connectivity
```bash
docker exec -it kawal-siber-proxy wget -qO- http://backend:8000/api/v1/health
# Expected: {"status":"healthy","database":"connected",...}

docker exec -it kawal-siber-proxy wget -qO- http://frontend:3000/
# Expected: HTML document containing KAWAL SIBER shell.
```

### STEP 15: Verify Ingress Reverse Proxy Health
```bash
curl -I http://localhost/healthz
# Expected: HTTP/1.1 200 OK
```

### STEP 16: Initial Browser Access (Staging IP Mode)
- Open browser: `http://YOUR_EC2_PUBLIC_IP/`
- Verify Dashboard, Asset list, and Reports render cleanly.

### STEP 17: Configure Domain & TLS/HTTPS (Certbot)
```bash
# 1. Install Certbot on host
sudo apt-get install -y certbot

# 2. Stop Nginx container temporarily to acquire standalone certificate
docker compose -f deploy/single-instance/compose.single-instance.yaml stop reverse-proxy

# 3. Obtain certificate
sudo certbot certonly --standalone -d your-domain.com --non-interactive --agree-tos -m admin@your-domain.com

# 4. Uncomment HTTPS block in deploy/single-instance/nginx.conf
# 5. Restart Nginx container
docker compose -f deploy/single-instance/compose.single-instance.yaml up -d reverse-proxy
```

### STEP 18: Final Production Verification
- Navigate to `https://your-domain.com/`
- Verify valid SSL certificate, HSTS headers, and 0 console errors.

---

## 8. Verification & Health-Check Checklist

| Check Item | Target | Verification Command | Expected Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Docker Engine** | Host | `docker info` | Active, running | **PASS** |
| **Compose Manifest** | Config | `docker compose -f ... config` | Valid YAML, 0 errors | **PASS** |
| **Reverse Proxy** | Ingress | `curl -sI http://localhost/healthz` | `HTTP/1.1 200 OK` | **PASS** |
| **Backend Liveness** | Internal API | `curl -s http://localhost/api/v1/health` | `status: healthy` | **PASS** |
| **Frontend SSR** | Web UI | `curl -s http://localhost/ \| grep "KAWAL SIBER"` | Matches HTML title | **PASS** |
| **Frontend API Proxy** | Next.js API | `curl -s http://localhost/api/v1/assets` | Returns JSON array | **PASS** |
| **Worker Queue Loop**| Worker Log | `docker compose logs worker \| grep "Polling"` | Active poll log | **PASS** |
| **SQLite Integrity** | Database | `python scripts/verify-sqlite-integrity.py` | `ok`, 0 FK errors | **PASS** |
| **Port Security** | Host Network| `sudo netstat -tlpn` | Only 22, 80, 443 listen | **PASS** |
| **Report Generation**| E2E | Generate report via Web UI | Valid PDF / JSON generated | **PASS** |
| **Data Persistence** | Volume | `docker compose restart && verify DB` | Data persists intact | **PASS** |

---

## 9. Operations, Backup & Maintenance

### Daily Operational Commands
```bash
# Check service health status
docker compose -f deploy/single-instance/compose.single-instance.yaml ps

# Stream logs
docker compose -f deploy/single-instance/compose.single-instance.yaml logs -f backend

# Restart a specific service
docker compose -f deploy/single-instance/compose.single-instance.yaml restart worker
```

### Safe Database Backup
SQLite WAL mode requires using the official SQLite backup API or `.backup` command to guarantee snapshot consistency:
```bash
BACKUP_DIR="/opt/kawal-siber/storage/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p "$BACKUP_DIR"

# Perform atomic, safe backup of live database
sqlite3 /opt/kawal-siber/storage/kawal_siber.db ".backup '$BACKUP_DIR/kawal_siber_$TIMESTAMP.db'"
gzip "$BACKUP_DIR/kawal_siber_$TIMESTAMP.db"

echo "Backup created at $BACKUP_DIR/kawal_siber_$TIMESTAMP.db.gz"
```

### Safe Application Update Procedure
```bash
cd /opt/kawal-siber

# 1. Capture current Git commit hash
PREV_COMMIT=$(git rev-parse HEAD)

# 2. Backup database
sqlite3 storage/kawal_siber.db ".backup 'storage/backups/pre_update_$(date +%s).db'"

# 3. Pull updates from approved main branch
git fetch origin main && git pull origin main
git submodule update --init --recursive

# 4. Rebuild affected images
docker compose -f deploy/single-instance/compose.single-instance.yaml build

# 5. Execute new migrations (if any)
docker compose -f deploy/single-instance/compose.single-instance.yaml run --rm backend alembic upgrade head

# 6. Recreate running services with zero data loss
docker compose -f deploy/single-instance/compose.single-instance.yaml up -d

# 7. Smoke test
curl -f http://localhost/healthz && curl -f http://localhost/api/v1/health

# ROLLBACK INSTRUCTION (If smoke test fails):
# git checkout $PREV_COMMIT
# docker compose -f deploy/single-instance/compose.single-instance.yaml up -d --build
```

> [!CAUTION]
> **NEVER** run `docker compose down -v`. The `-v` flag deletes named volumes and will destroy your operational state.

---

## 10. Proxmox Portability (VM vs LXC)

### Recommended: Proxmox QEMU Virtual Machine (KVM)
- **Guest OS**: Ubuntu Server 24.04 LTS x86_64.
- **Hardware Allocation**: 4 vCPUs, 16 GB RAM, 100 GB VirtIO disk.
- **Compatibility**: **100% Identical to EC2**. Uses the standard Linux kernel without container virtualization restrictions. Docker Engine, Compose, and SQLite WAL run natively without modifications.

### Optional: Proxmox Unprivileged LXC Container
Running Docker inside a Proxmox LXC container requires specific configuration in `/etc/pve/lxc/<CTID>.conf`:
```ini
features: nesting=1,keyctl=1
```
#### Known Limitations & Requirements:
1. **Nesting & Keyctl**: Required for containerd overlayfs and systemd in LXC.
2. **Storage Driver**: Proxmox ZFS storage requires configuring Docker daemon to use `vfs` or setting up an ext4 sub-volume mounted into `/var/lib/docker` to avoid overlayfs-on-ZFS performance degradation.
3. **AppArmor / Capabilities**: Nmap raw packet scanning (`-sS`) requires `CAP_NET_RAW` and `CAP_NET_ADMIN`. If unprivileged LXC drops these capabilities, Nmap must run in unprivileged TCP connect mode (`-sT`).

---

## 11. Known Blockers, Limitations & Future Architecture

1. **Host-Level Single Point of Failure (SPOF)**: This architecture runs on one host. If the EC2 instance or Proxmox host fails, downtime occurs until the host restarts.
2. **SQLite Concurrent Writer Limit**: SQLite supports multiple readers but serializes writes. This is well-suited for hackathon workloads, but large-scale enterprise deployments (>100 RPS) should transition to PostgreSQL.
3. **Future Architecture**: The multi-instance AWS ECS / RDS / ALB redundancy design is preserved in [`deploy/aws-ec2/README.md`](../aws-ec2/README.md) and [`docs/deployment/aws-ec2/`](../../docs/deployment/aws-ec2/) as the **Level 2 Future Architecture**.

