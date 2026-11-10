# KAWAL SIBER — Deployment Guide

## 1. Deployment Overview

KAWAL SIBER supports a progressive deployment roadmap:

1. **ACTIVE PRODUCTION TARGET — Single-Host Linux (EC2 / Proxmox VM / LXC)**:
   - **Canonical Runbook**: [`deploy/single-instance/README.md`](./single-instance/README.md)
   - **Manifest**: [`deploy/single-instance/compose.single-instance.yaml`](./single-instance/compose.single-instance.yaml)
   - **Architecture**: Single Linux host (Ubuntu 24.04 LTS), Docker Engine & Compose. Nginx reverse proxy on 80/443; internal Next.js frontend (:3000), FastAPI backend (:8000), and Celery worker. Backed by persistent host SQLite (`storage/kawal_siber.db`) and WAL mode.
   - **Target Portability**: Amazon EC2 (`m7i.xlarge` / `t3.xlarge`), Proxmox QEMU VM, or Proxmox unprivileged LXC. Zero dependency on AWS managed services.

2. **Local Windows Development**:
   - Direct process execution (Uvicorn + Next.js Standalone + Worker Daemon) on loopback (`127.0.0.1`) backed by SQLite WAL mode.
   - Script: [`scripts/start-local-dev.ps1`](../scripts/start-local-dev.ps1).

3. **FUTURE ARCHITECTURE (LEVEL 2) — AWS Distributed EC2 Container Redundancy**:
   - Reference: [`deploy/aws-ec2/README.md`](./aws-ec2/README.md) *(Marked as Future Roadmap / Staging only)*.
   - 6 dedicated EC2 instances running 2 containers each (12 containers total) with PostgreSQL streaming replication.

4. **FUTURE ARCHITECTURE (LEVEL 3) — AWS ECS Multi-AZ Enterprise**:
   - Reference: [`docs/deployment/aws-ec2/15-CICD-ARCHITECTURE.md`](../docs/deployment/aws-ec2/15-CICD-ARCHITECTURE.md) and [`infra/aws/`](../infra/aws/).
   - AWS ECS on EC2 auto-spread across multiple AZs fronted by Application Load Balancer and Amazon RDS PostgreSQL Multi-AZ.

---

## 2. Deployment Topology Comparison

| Feature / Metric | Active Target: Single Linux Host | Local Windows Dev | Future: Distributed EC2 | Future: ECS Multi-AZ |
| :--- | :--- | :--- | :--- | :--- |
| **Guide** | **[`deploy/single-instance/`](./single-instance/)** | Root [`scripts/`](../scripts/) | [`deploy/aws-ec2/`](./aws-ec2/) | [`infra/aws/`](../infra/aws/) |
| **Target Host** | 1 Host (EC2 / Proxmox VM / LXC) | Local Windows Workstation | 6 Dedicated EC2 Hosts | Auto-scaled ECS Cluster |
| **Primary Persistence** | SQLite (`kawal_siber.db`) Host Mount | SQLite Localhost Socket | PostgreSQL 16 Streaming Replication | Amazon RDS Multi-AZ |
| **Ingress Layer** | Nginx Reverse Proxy (80/443) | Localhost sockets (3000/8000) | Nginx Ingress Active/Active | AWS Application Load Balancer |
| **Container Instances** | 4 (Proxy, Frontend, Backend, Worker)| Zero (Native processes) | 12 core containers (2/host) | 8+ ECS tasks auto-spread |
| **Cloud Dependencies** | **None** (Self-contained) | None | EC2, VPC, Security Groups | ECS, ECR, RDS, ALB, IAM OIDC |
| **High Availability** | Single-host test/staging | None (Single developer) | Container-level only | Full Multi-AZ Host & Data HA |
| **Status** | **ACTIVE PRIMARY DEPLOYMENT** | Development only | Future Roadmap | Future Enterprise Target |

---

## 3. Directory Layout

- [`deploy/single-instance/`](./single-instance): **CANONICAL ACTIVE RUNBOOK** for standalone Linux deployment (Nginx, Docker Compose, EC2 specifications, Proxmox portability, operations, backup/restore).
- [`deploy/aws/`](./aws): Per-host compose configurations and migration scripts for the 6-host EC2 topology (Future Roadmap).
- [`deploy/aws-ec2/`](./aws-ec2): Redundancy runbook for distributed 6-host EC2 topology (Future Roadmap).
- [`infra/aws/`](../infra/aws): CloudFormation/JSON infrastructure specifications for AWS ECS, ECR, ALB, IAM, and RDS (Future Enterprise Target).
