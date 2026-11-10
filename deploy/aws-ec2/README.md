# KAWAL SIBER — AWS EC2 Distributed Container Redundancy Runbook

## 1. Six EC2 Host Roles & Minimum 12 Core Containers

The AWS EC2 Distributed Deployment topology mandates running **at least two independent containers on each of the six EC2 hosts**:

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

## 2. Host-by-Host Setup & Configuration

### 2.1 Database Host (`ks-db-01`)
- **Containers**: `postgres-primary` (5432) and `postgres-standby` (5433).
- **Storage Layout**:
  - `/ebs/primary/pgdata`: Mount for Primary DB.
  - `/ebs/standby/pgdata`: Mount for Standby DB.
  - `/ebs/shared/wal_archive`: Shared volume for WAL segments.
- **Replication**: Physical streaming replication using user `replicator` and slot `standby_slot`.
- **Failover Promotion**: If primary fails, execute `docker exec -it postgres-standby /usr/local/bin/promote-standby.sh` (RTO < 5s, RPO = 0).

### 2.2 Frontend Host (`ks-frontend-01`)
- **Containers**: `frontend-a` (3001) and `frontend-b` (3002).
- **Runtime**: Next.js 15 standalone server (`node server.js`).
- **Static Assets**: Synchronized across containers via Docker image layers.
- **Health Check**: `curl http://127.0.0.1:3001/` and `3002/`.

### 2.3 Backend API Host (`ks-backend-01`)
- **Containers**: `backend-a` (8001) and `backend-b` (8002).
- **Runtime**: FastAPI with Uvicorn.
- **Session Handling**: Stateless JWT authentication; zero in-memory session pinning.
- **Connection Pool**: Sized to 20 base connections + 10 overflow per container (total 60 max connections).

### 2.4 Worker Host (`ks-worker-01`)
- **Containers**: `worker-a` and `worker-b`.
- **Queue Concurrency**: PostgreSQL `SELECT ... FOR UPDATE SKIP LOCKED` eliminates race conditions.
- **Heartbeat**: Each container heartbeats to `/tmp/worker_heartbeat`.
- **Fault Recovery**: Automatic reclamation of stale jobs older than 10 minutes.

### 2.5 Security Tools Host (`ks-tools-01`)
- **Containers**: `tools-agent-a` (9001) and `tools-agent-b` (9002).
- **Execution Engine**: Nmap, Suricata CLI, and Deep Eye models.
- **Scope Guard**: In-container validation prevents scanning loopback, metadata (169.254.169.254), or unauthorized CIDRs.
- **Concurrency**: `asyncio.Semaphore(4)` per container.

### 2.6 Load Balancer Host (`ks-lb-01`)
- **Containers**: `nginx-a` (8081) and `nginx-b` (8082).
- **Upstreams**: Round-robin and least-connection proxying to `frontend_cluster` and `backend_cluster`.
- **Passive Health Check**: `max_fails=2 fail_timeout=5s` with automated `proxy_next_upstream` retry.
- **ALB Ingress**: Targets registered with AWS Application Load Balancer across 2+ Availability Zones.

---

## 3. Security Groups & Secrets Management

- **Security Groups**: Principle of least privilege enforced; database ports 5432/5433 accessible only by backend, worker, and replication IPs.
- **Secrets**: Injected from AWS Secrets Manager or SSM Parameter Store at boot; no plaintext passwords in compose files or images.

---

## 4. Operational Level Disclosures

> [!IMPORTANT]
> **LEVEL 1 CONTAINER REDUNDANCY**: This topology eliminates container-level SPOFs. However, each EC2 instance remains a single physical failure domain. For true host-level and AZ-level High Availability (Level 2), migrate the database to **Amazon RDS Multi-AZ** and stateless tiers to **AWS ECS on EC2 across multiple Availability Zones**.
