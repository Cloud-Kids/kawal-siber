# KAWAL SIBER — AWS EC2 Distributed Container Redundancy Architecture

## Executive Summary & Architecture Overview

This deployment package implements the **AWS EC2 Distributed Container Redundancy Architecture** for **KAWAL SIBER (Sistem Pertahanan Siber Teritorial — Kartika Cyber Hackathon 2026)**.

The deployment topology maintains the **six dedicated EC2 roles**, with **every role running at least two independent containers (12 core containers total)** to eliminate single container points of failure.

```
                              PUBLIC INTERNET
                                     │
                      [ AWS Application Load Balancer ]
                        (Multi-AZ: Ingress & TLS ACM)
                                     │
             ┌───────────────────────┴───────────────────────┐
             │ Port 8081                                     │ Port 8082
             ▼                                               ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │  EC2 HOST 6: ks-lb-01 (Reverse Proxy Cluster)                   │
    │  ├── nginx-a (Container on 8081)                                │
    │  └── nginx-b (Container on 8082)                                │
    └───────────────────────┬─────────────────────────────────────────┘
                            │ Internal VPC Network (10.0.0.0/16)
             ┌──────────────┴──────────────┬──────────────────────────┐
             ▼                             ▼                          ▼
┌─────────────────────────┐   ┌─────────────────────────┐   ┌─────────────────────────┐
│ EC2 HOST 2:             │   │ EC2 HOST 3:             │   │ EC2 HOST 5:             │
│ ks-frontend-01          │   │ ks-backend-01           │   │ ks-tools-01             │
│ (Next.js 15 Standalone) │   │ (FastAPI REST API)      │   │ (Security Execution)    │
│ ├── frontend-a (3001)   │   │ ├── backend-a (8001)    │   │ ├── tools-agent-a (9001)│
│ └── frontend-b (3002)   │   │ └── backend-b (8002)    │   │ └── tools-agent-b (9002)│
└─────────────────────────┘   └────────────┬────────────┘   └────────────▲────────────┘
                                           │                             │
                                           │ SQL Connection Pool         │ Internal Tool Invocation
                                           ▼                             │
                              ┌─────────────────────────┐                │
                              │ EC2 HOST 1:             │                │
                              │ ks-db-01                │                │
                              │ (PostgreSQL 16 HA)      │                │
                              │ ├── postgres-primary    │                │
                              │ │   (Port 5432 - RW)    │                │
                              │ └── postgres-standby    │                │
                              │     (Port 5433 - RO)    │                │
                              └────────────▲────────────┘                │
                                           │                             │
                                           │ Claim Queue (SKIP LOCKED)   │
                                           ▼                             │
                              ┌─────────────────────────┐                │
                              │ EC2 HOST 4:             │                │
                              │ ks-worker-01            │                │
                              │ (Async Worker Pool)     │                │
                              │ ├── worker-a            ├────────────────┘
                              │ └── worker-b            │
                              └─────────────────────────┘
```

---

## 1. Six EC2 Hosts — Minimum 12 Core Containers

| Host Role | Host Name | Container 1 | Container 2 | Mode | In-Host Network Ports | Primary Responsibility |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Database** | `ks-db-01` | `postgres-primary` | `postgres-standby` | Primary / Standby | `5432` (RW) / `5433` (RO) | Persistent ACID storage, physical streaming replication, WAL archiving |
| **Frontend** | `ks-frontend-01` | `frontend-a` | `frontend-b` | Active / Active | `3001` / `3002` | Next.js 15 standalone server, UI routes, client state |
| **Backend API** | `ks-backend-01` | `backend-a` | `backend-b` | Active / Active | `8001` / `8002` | FastAPI REST services, JWT validation, DB connection pool |
| **Worker** | `ks-worker-01` | `worker-a` | `worker-b` | Active / Active | Host network / internal | Async job execution, atomic claim via `FOR UPDATE SKIP LOCKED` |
| **Security Tools** | `ks-tools-01` | `tools-agent-a` | `tools-agent-b` | Active / Active | `9001` / `9002` | Nmap, Suricata CLI, Deep Eye, in-container scope enforcement |
| **Load Balancer** | `ks-lb-01` | `nginx-a` | `nginx-b` | Active / Active | `8081` / `8082` | Reverse proxy, rate limiting, SSL termination support, ALB targets |

---

## 2. Level 1 (Container Redundancy) vs Level 2 (Host / AZ High Availability)

> [!IMPORTANT]
> **CRITICAL ARCHITECTURAL DISTINCTION**
> This deployment strictly implements **Level 1: Container-Level Redundancy**. It runs at least two containers on a single EC2 host per role. It is **NOT** a full Multi-Host or Multi-AZ High Availability (Level 2) deployment.

### What Level 1 Protects Against:
- Individual container crashes (OOM kills, unhandled exceptions, segfaults).
- Application process deadlocks or internal thread panics.
- Isolated container configuration errors during canary or rolling container upgrades.
- Ephemeral container filesystem corruption.
- Single container network socket hang.

### What Level 1 DOES NOT Protect Against:
- Underlying EC2 hardware failure (CPU/RAM faults, hypervisor crash).
- AWS Availability Zone power, network, or hardware outages.
- Root EBS volume corruption or detach on the EC2 host.
- Host Linux kernel panic, out-of-memory kernel killer, or host OS lockup.
- Host network interface failure (ENI throttling or physical NIC drops).

### Single Points of Failure (SPOFs) at Level 1:
- Each of the 6 EC2 instances represents a host-level SPOF. If `ks-db-01` dies at the hardware level, both `postgres-primary` and `postgres-standby` fail simultaneously because they reside on the same hypervisor.
- **Why Level 1 is NOT full production HA**: In mission-critical defense operations, an AZ failure or host degradation would take down an entire tier.
- **Roadmap to Level 2 (True HA)**:
  1. Migrate database from `ks-db-01` containers to **Amazon RDS Multi-AZ PostgreSQL** or **Aurora Global Database**.
  2. Deploy stateless tiers (`frontend`, `backend`, `worker`, `tools`) via **Amazon ECS on EC2 Auto Scaling Groups** spanning at least 2 Availability Zones (`ap-southeast-1a` and `ap-southeast-1b`).
  3. Replace `ks-lb-01` Nginx proxy tier entirely with native **AWS Application Load Balancer** routing directly to target groups across multiple AZs.

---

## 3. Orchestration & Recovery Strategy

### Chosen Approach: Modular Docker Compose with systemd Supervision
For the Kartika Cyber Hackathon 2026 deployment topology:
- Each EC2 host runs an independent `docker-compose.yml` tailored strictly to its role.
- Containers specify `restart: unless-stopped`.
- Systemd manages the Docker daemon and service lifecycle (`/etc/systemd/system/kawal-role.service`).
- Health checks execute every 10–15 seconds with auto-restart on 3 consecutive failures.
- **Why Not Docker Swarm**: Swarm introduces overlay network latency and split-brain raft consensus complexity across only 6 nodes without providing true cross-AZ resiliency.
- **Why ECS on EC2 is the Enterprise Path**: For full cloud-native operations, AWS ECS task definitions with `desiredCount: 2` and host role placement constraints (`attribute:role == ks-backend`) provide automated cluster-level recovery.

---

## 4. Health Check & Failover Matrix (All 12 Containers)

| Host | Container Name | Role | Port / Mode | Health Check Method | Interval / Timeout / Retries | Failover Behavior & RTO | RPO (Data Loss Risk) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ks-db-01` | `postgres-primary` | Database RW | 5432 (TCP) | `pg_isready -U kawal_user -d kawal_siber -p 5432` | 10s / 5s / 3 retries | Standby promoted via `promote-standby.sh` (RTO: < 5s) | RPO: 0 (synchronous/near-zero lag streaming) |
| `ks-db-01` | `postgres-standby` | Database RO/Hot Standby | 5433 (TCP) | `pg_isready -U kawal_user -d kawal_siber -p 5432` | 10s / 5s / 3 retries | Primary continues writes. Standby auto-restarts (RTO: 10s) | RPO: 0 |
| `ks-frontend-01` | `frontend-a` | UI Server A | 3001 (HTTP) | `wget --spider http://127.0.0.1:3000/` | 15s / 5s / 3 retries | Nginx marks down; 100% routed to frontend-b (RTO: 0s) | RPO: 0 (Stateless) |
| `ks-frontend-01` | `frontend-b` | UI Server B | 3002 (HTTP) | `wget --spider http://127.0.0.1:3000/` | 15s / 5s / 3 retries | Nginx marks down; 100% routed to frontend-a (RTO: 0s) | RPO: 0 (Stateless) |
| `ks-backend-01` | `backend-a` | API Server A | 8001 (HTTP) | `GET /api/v1/health` | 10s / 5s / 3 retries | Nginx routes to backend-b; JWT remains valid (RTO: 0s) | RPO: 0 (Stateless) |
| `ks-backend-01` | `backend-b` | API Server B | 8002 (HTTP) | `GET /api/v1/health` | 10s / 5s / 3 retries | Nginx routes to backend-a; JWT remains valid (RTO: 0s) | RPO: 0 (Stateless) |
| `ks-worker-01` | `worker-a` | Background Consumer A | Internal | `/tmp/worker_heartbeat` mtime < 30s | 15s / 5s / 3 retries | worker-b consumes pending/stale jobs after lease timeout (RTO: 10m) | RPO: 0 (Atomic DB transaction rollback) |
| `ks-worker-01` | `worker-b` | Background Consumer B | Internal | `/tmp/worker_heartbeat` mtime < 30s | 15s / 5s / 3 retries | worker-a consumes pending/stale jobs after lease timeout (RTO: 10m) | RPO: 0 (Atomic DB transaction rollback) |
| `ks-tools-01` | `tools-agent-a` | Tools Agent A | 9001 (HTTP) | `curl -f http://127.0.0.1:9000/health` | 15s / 5s / 3 retries | Worker client fails over to tools-agent-b (9002) (RTO: < 2s) | RPO: 0 (Job retried or marked failed cleanly) |
| `ks-tools-01` | `tools-agent-b` | Tools Agent B | 9002 (HTTP) | `curl -f http://127.0.0.1:9000/health` | 15s / 5s / 3 retries | Worker client fails over to tools-agent-a (9001) (RTO: < 2s) | RPO: 0 (Job retried or marked failed cleanly) |
| `ks-lb-01` | `nginx-a` | Reverse Proxy A | 8081 (HTTP) | `curl -f http://127.0.0.1/nginx-health` | 10s / 3s / 3 retries | AWS ALB shifts 100% traffic to nginx-b (8082) (RTO: < 10s) | RPO: 0 (Stateless proxy) |
| `ks-lb-01` | `nginx-b` | Reverse Proxy B | 8082 (HTTP) | `curl -f http://127.0.0.1/nginx-health` | 10s / 3s / 3 retries | AWS ALB shifts 100% traffic to nginx-a (8081) (RTO: < 10s) | RPO: 0 (Stateless proxy) |

---

## 5. Database Redundancy Deep Dive

### Volume Layout & Separation:
- **EBS Volume 1** (`/ebs/primary/pgdata`): Dedicated ext4/xfs volume for `postgres-primary`.
- **EBS Volume 2** (`/ebs/standby/pgdata`): Dedicated ext4/xfs volume for `postgres-standby`.
- **EBS Volume 3** (`/ebs/shared/wal_archive`): Shared archive volume for fallback WAL segment retention.

### Replication Mechanism:
- Physical Streaming Replication using PostgreSQL 16 replication protocol.
- Dedicated `replicator` role with SCRAM-SHA-256 credentials.
- Physical replication slot `standby_slot` prevents WAL segment recycling before the standby confirms receipt.
- Standby configured with `hot_standby = on` and `primary_conninfo`.

### Promotion & Failover Procedure:
1. Primary failure detected (e.g. `docker inspect -f '{{.State.Running}}' postgres-primary` returns false).
2. Automation script or operator executes:
   ```bash
   docker exec -it postgres-standby /usr/local/bin/promote-standby.sh
   ```
3. Standby applies remaining WAL records, exits recovery mode, and begins accepting read-write traffic on port `5433`.
4. Backend API connection strings or internal DNS record updated to route writes to port `5433`.

### Zero-Data-Loss SQLite to PostgreSQL Migration:
- Executed via `kawal-siber/deploy/aws/migrations/sqlite_to_postgres.py`.
- Migrates all 16 tables in foreign-key dependency order.
- Post-migration row counts and sequence values automatically reconciled.

---

## 6. Worker Queue Concurrency Deep Dive

### Atomic Claim with `SELECT ... FOR UPDATE SKIP LOCKED`:
In PostgreSQL, multiple concurrent workers poll the same table without race conditions:
```sql
SELECT * FROM scan_jobs
WHERE status = 'PENDING'
ORDER BY created_at ASC
LIMIT 1
FOR UPDATE SKIP LOCKED;
```
- When `worker-a` executes this query, PostgreSQL places a row-level lock on the chosen record.
- If `worker-b` queries at the exact same millisecond, PostgreSQL automatically skips the locked row and claims the next pending row.
- **Zero Lock Collisions**: Neither worker blocks, and no duplicate claims occur.

### Stale Job Recovery:
- Every worker container periodically runs `recover_stale_running_scans` and `recover_stale_running_reports`.
- Any job with `status = 'RUNNING'` and `started_at < (now() - 10 minutes)` is reset to `PENDING` with an explanatory recovery message.

---

## 7. Security Tools Agent Redundancy Deep Dive

### Microservice Isolation:
- `tools-agent-a` and `tools-agent-b` run as unprivileged user `toolsuser` (UID 1002).
- Neither tool container requires root privileges to execute authorized scans (`-sT` unprivileged TCP connect scan).
- All requests require `X-Agent-Key` header authentication.

### In-Container Scope Enforcement:
- Prior to executing `nmap`, the agent parses the target IP and validates it against `allowed_cidr` using Python `ipaddress`.
- Loopback (`127.0.0.0/8`), Link-Local / Cloud Metadata (`169.254.0.0/16`), and Multicast (`224.0.0.0/4`) are unconditionally blocked at the application level.

### Concurrency Semaphore:
- Limited to `MAX_CONCURRENT_SCANS=4` per container via `asyncio.Semaphore`.
- Prevents CPU spikes and memory exhaustion during parallel task execution.

---

## 8. Load Balancer & Traffic Routing Deep Dive

### Upstream Passive Failover:
```nginx
upstream backend_cluster {
    least_conn;
    server ks-backend-01:8001 max_fails=2 fail_timeout=5s;
    server ks-backend-01:8002 max_fails=2 fail_timeout=5s;
    keepalive 32;
}
```
If `backend-a` fails to respond or returns HTTP 502/503, Nginx immediately re-routes the in-flight request to `backend-b` via `proxy_next_upstream` without client disruption.

### AWS ALB Integration:
- ALB Target Group 1: `ks-lb-01:8081` (nginx-a)
- ALB Target Group 2: `ks-lb-01:8082` (nginx-b)
- Health check path: `/nginx-health` (HTTP 200).
- TLS terminated at the ALB using AWS Certificate Manager (ACM) with modern cipher suites (`ELBSecurityPolicy-TLS13-1-2-2021-06`).

---

## 9. Resource Capacity Planning & Monthly AWS Cost

| EC2 Host | Instance Type | vCPU / RAM | Storage (EBS gp3) | Primary Roles & Containers | Estimated Monthly Cost (ap-southeast-1) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ks-db-01` | `t4g.xlarge` | 4 vCPU / 16 GB | 200 GB gp3 (3000 IOPS, 125 MB/s) | `postgres-primary`, `postgres-standby` | \$118.50 |
| `ks-frontend-01` | `t4g.medium` | 2 vCPU / 4 GB | 50 GB gp3 (3000 IOPS) | `frontend-a`, `frontend-b` | \$33.20 |
| `ks-backend-01` | `t4g.large` | 2 vCPU / 8 GB | 60 GB gp3 (3000 IOPS) | `backend-a`, `backend-b` | \$65.40 |
| `ks-worker-01` | `t4g.large` | 2 vCPU / 8 GB | 60 GB gp3 (3000 IOPS) | `worker-a`, `worker-b` | \$65.40 |
| `ks-tools-01` | `t4g.large` | 2 vCPU / 8 GB | 80 GB gp3 (3000 IOPS) | `tools-agent-a`, `tools-agent-b` | \$67.20 |
| `ks-lb-01` | `t4g.small` | 2 vCPU / 2 GB | 30 GB gp3 (3000 IOPS) | `nginx-a`, `nginx-b` | \$18.60 |
| **AWS ALB** | Application Load Balancer | Managed | N/A | Public Ingress across 2 AZs | \$22.50 |
| **S3 Storage** | Standard S3 Bucket | Managed | 100 GB + API calls | Reports, PCAP, Scans, Evidence | \$3.50 |
| **AWS KMS** | Customer Managed Key | Managed | N/A | S3 SSE-KMS & Secrets Manager | \$2.00 |
| **CloudWatch** | Logs & Metrics | Managed | 10 GB ingested | Container logs, alarms, metrics | \$6.80 |
| **TOTAL** | — | **14 vCPU / 46 GB** | **480 GB gp3 + S3** | **12 Core Containers across 6 EC2** | **\$403.10 / month** |

---

## 10. Network Topology & Security Groups Matrix

### VPC Layout:
- VPC CIDR: `10.0.0.0/16` in `ap-southeast-1` (Singapore)
- Public Subnet AZ1: `10.0.1.0/24` (`ap-southeast-1a`) — ALB Ingress
- Public Subnet AZ2: `10.0.2.0/24` (`ap-southeast-1b`) — ALB Ingress
- Private App Subnet AZ1: `10.0.10.0/24` (`ap-southeast-1a`) — EC2 instances
- Private App Subnet AZ2: `10.0.20.0/24` (`ap-southeast-1b`) — Reserved for Level 2 expansion

### Security Groups Rules Matrix:

| Security Group | Inbound Source | Protocol & Port | Destination | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `sg-kawal-alb` | `0.0.0.0/0` | TCP 443 / 80 | ALB | Public HTTPS ingress from operators |
| `sg-kawal-lb` | `sg-kawal-alb` | TCP 8081, 8082 | `ks-lb-01` | ALB forward to Nginx containers |
| `sg-kawal-frontend` | `sg-kawal-lb` | TCP 3001, 3002 | `ks-frontend-01` | Nginx reverse proxy to Next.js |
| `sg-kawal-backend` | `sg-kawal-lb`, `ks-frontend-01` | TCP 8001, 8002 | `ks-backend-01` | Nginx & SSR calls to FastAPI |
| `sg-kawal-tools` | `ks-backend-01`, `ks-worker-01` | TCP 9001, 9002 | `ks-tools-01` | Authenticated tool execution requests |
| `sg-kawal-db` | `ks-backend-01`, `ks-worker-01`, `ks-db-01` | TCP 5432, 5433 | `ks-db-01` | PostgreSQL database & streaming replication |
| `sg-kawal-bastion` | Authorized Admin CIDR | TCP 22 (SSH) | Bastion Host | Secure jump host administration |

---

## 11. Logging, Monitoring & Alerting

### Centralized Logging:
- AWS CloudWatch Logs Agent / Fluent Bit sidecar shipping container stdout/stderr.
- Log groups: `/aws/ec2/kawal-siber/{db,backend,frontend,worker,tools,lb}`.

### Five Critical CloudWatch Alarms:
1. **Standby Replication Lag Alert**:
   - Metric: `PostgreSQL/ReplicationLagBytes > 10485760` (10 MB) or `LagSeconds > 60` for 3 consecutive evaluation periods.
   - Severity: HIGH.
2. **Container Crash / Flapping Alert**:
   - Metric: `ContainerRestartCount > 3` within 10 minutes.
   - Severity: CRITICAL.
3. **Worker Queue Depth Alert**:
   - Metric: `Queue/PendingJobs > 50` or `OldestPendingJobAge > 300 seconds`.
   - Severity: MEDIUM.
4. **Backend API 5xx Error Rate**:
   - Metric: `HTTPCode_Backend_5XX / TotalRequests > 0.01` (1%) over 5 minutes.
   - Severity: HIGH.
5. **EC2 Host Resource Starvation**:
   - Metric: `CPUUtilization > 85%` or `DiskSpaceUtilization > 80%` on any host.
   - Severity: HIGH.

---

## 12. Configuration Management & Secrets

- Plaintext secrets are strictly prohibited in repository files and Docker images.
- AWS Systems Manager (SSM) Parameter Store or AWS Secrets Manager stores all credentials:
  - `/kawal-siber/prod/db_password`
  - `/kawal-siber/prod/jwt_secret`
  - `/kawal-siber/prod/tools_agent_key`
- Host startup scripts fetch parameters via IAM Instance Profiles at container startup and inject them into container environments in-memory.

---

## 13. Artifact & Evidence Storage Redundancy

- Storage destination: Amazon S3 Bucket `kawal-siber-evidence-prod-{AccountId}`.
- Encryption: Server-Side Encryption with AWS KMS (`aws:kms`).
- Redundancy: S3 standard provides 99.999999999% (11 9's) data durability across multiple AZs.
- Versioning: Enabled to prevent accidental deletion or tampering.
- Lifecycle Rules: Transition raw PCAP and scan XML to S3 Glacier Flexible Retrieval after 90 days; expire temporary debug logs after 30 days.

---

## 14. Failure Test Scenarios Runbook Status

The automated failure verification runbook is located in `tests/run_failure_scenarios.py`.

| Scenario ID | Test Description | Target Role | Current Status | Disclosed Verification Note |
| :--- | :--- | :--- | :--- | :--- |
| `SCENARIO-01` | Database Primary Kill & Standby Promotion | `ks-db-01` | **NOT RUN** | AWS staging cluster not provisioned in local dev environment. |
| `SCENARIO-02` | Frontend Container A Crash & Active Failover | `ks-frontend-01` | **NOT RUN** | AWS EC2 instance not provisioned locally. |
| `SCENARIO-03` | Backend API Container A Kill & Session Continuity | `ks-backend-01` | **NOT RUN** | AWS EC2 instance not provisioned locally. |
| `SCENARIO-04` | Worker A Mid-Execution Crash & Stale Reclaim | `ks-worker-01` | **NOT RUN** | Distributed PostgreSQL worker pool not active locally. |
| `SCENARIO-05` | Security Tools Agent Failure & Warm Failover | `ks-tools-01` | **NOT RUN** | Tools agent cluster not provisioned locally. |
| `SCENARIO-06` | Load Balancer Nginx Crash & ALB Reroute | `ks-lb-01` | **NOT RUN** | AWS ALB target group requires cloud VPC deployment. |
| `SCENARIO-07` | High Concurrency Job Submission (Zero-Collision) | `ks-worker-01` | **NOT RUN** | AWS multi-worker pool not active locally. |
| `SCENARIO-08` | Network Partition Between Hosts & Alert Fired | Cross-Host | **NOT RUN** | Multi-host cloud network not provisioned locally. |

---

## 15. Honest Architectural Assessment & Readiness Status

> [!CAUTION]
> **OFFICIAL PRODUCTION READINESS STATUS**:
> **`NOT PRODUCTION-READY FOR THE PUBLIC INTERNET`**
>
> 1. **Level 1 Limitation**: Running two containers per role on a single EC2 host protects against container crashes, but **does not protect against EC2 host failure or Availability Zone failure**.
> 2. **Security Controls Remaining**: Complete deployment requires end-to-end mTLS certificates, AWS IAM role lockdown, and external web application firewall (AWS WAF) rules.
> 3. **Migration Prerequisite**: Operational data migration from SQLite to PostgreSQL must be executed and validated prior to cutting over production traffic.

