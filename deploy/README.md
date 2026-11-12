# KAWAL SIBER — Deployment Guide

## 1. Deployment Overview

KAWAL SIBER has exactly **one active deployment architecture**:

**ACTIVE PRODUCTION TARGET — Single-Host Linux (AWS EC2 / Proxmox VM / LXC)**:

- **Canonical Runbook**: [`deploy/single-instance/README.md`](./single-instance/README.md)
- **Manifest**: [`deploy/single-instance/compose.single-instance.yaml`](./single-instance/compose.single-instance.yaml)
- **Architecture**: Single Linux host (Ubuntu 24.04 LTS), Docker Engine & Compose. Nginx reverse proxy on 80/443; internal Next.js frontend (:3000), FastAPI backend (:8000), and worker daemon. Backed by persistent host SQLite (`storage/kawal_siber.db`) and WAL mode.
- **Target Portability**: Amazon EC2 (`m7i.xlarge` / `t3.xlarge`), Proxmox QEMU VM, or Proxmox unprivileged LXC. Zero dependency on AWS managed services.
- **AWS IaC**: [`iac/tf-aws/`](../iac/tf-aws/) provisions exactly one `aws_instance` + one `aws_security_group`.

**Local Windows Development**:

- Direct process execution (Uvicorn + Next.js + Worker Daemon) on loopback (`127.0.0.1`) backed by SQLite WAL mode.
- Root [`compose.yaml`](../compose.yaml) is the local Docker evaluation stack (loopback-only bindings, named volumes, `SCAN_ENABLED=false`) — **not** the production manifest.
- Script: [`scripts/start-local-dev.ps1`](../scripts/start-local-dev.ps1).

## 2. Compose Configuration Roles

| File | Role | Ingress | Persistence |
| :--- | :--- | :--- | :--- |
| [`compose.yaml`](../compose.yaml) (root) | Local development / evaluation | `127.0.0.1:3000`, `127.0.0.1:8000` | Named volumes (`kawal_siber_db`, `kawal_siber_reports`) |
| [`deploy/single-instance/compose.single-instance.yaml`](./single-instance/compose.single-instance.yaml) | **Production single-host** | Nginx reverse proxy `80/443` only | Host bind mounts (`storage/`) |

## 3. Directory Layout

- [`deploy/single-instance/`](./single-instance): **CANONICAL ACTIVE RUNBOOK** for standalone Linux deployment (Nginx, Docker Compose, EC2 specifications, Proxmox portability, operations, backup/restore).
- [`deploy/proxmox/`](./proxmox): Placeholder for the Proxmox VE deployment target (see [`iac/tf-proxmox/`](../iac/tf-proxmox/)).

## 4. Future Roadmap

A future High-Availability architecture (multi-host redundancy,
PostgreSQL replication, or managed services such as ECS/RDS) may be
designed separately. It is **not** part of the active deployment and no
obsolete multi-instance configuration is retained in this repository.
Any future CD pipeline requires explicit security design before
implementation (see [`docs/deployment/README.md`](../docs/deployment/README.md)).
