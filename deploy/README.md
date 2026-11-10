# KAWAL SIBER — Deployment Guide

## 1. Deployment Overview

KAWAL SIBER supports three progressive deployment modes:
1. **Localhost Windows Development**: Direct process execution (Uvicorn + Next.js Standalone + Worker Daemon) on loopback (`127.0.0.1`) backed by SQLite WAL mode.
2. **Local Docker Compose**: 3-service containerized stack (`compose.yaml`) for container testing and local evaluation.
3. **AWS Distributed Production**:
   - **Level 1 (EC2 Container Redundancy)**: 6 dedicated EC2 roles running at least 2 containers each (12 core containers total).
   - **Level 2 (ECS Multi-AZ Enterprise)**: AWS ECS on EC2 across at least 2 Availability Zones (`ap-southeast-1a` and `ap-southeast-1b`) fronted by an Application Load Balancer and backed by Amazon RDS PostgreSQL Multi-AZ.

---

## 2. Deployment Topology Comparison

| Feature / Metric | Mode 1: Local Windows Dev | Mode 2: Docker Compose | Mode 3: AWS EC2 (Level 1) | Mode 4: AWS ECS Multi-AZ (Level 2) |
| :--- | :--- | :--- | :--- | :--- |
| **Primary Persistence** | SQLite (`kawal_siber.db`) | SQLite Named Volume | PostgreSQL 16 Streaming Replication | Amazon RDS PostgreSQL Multi-AZ |
| **Ingress Layer** | Localhost sockets (3000/8000) | Bridge Port Mapping | Nginx Active/Active Upstream | AWS Application Load Balancer |
| **Container Instances** | Zero (Native processes) | 3 single containers | 12 core containers (2/host) | 8+ ECS tasks auto-spread |
| **High Availability** | None (Single developer) | None (Dev stack) | Container-level only | Full Multi-AZ Host & Data HA |
| **Production Readiness**| Development only | Testing / Evaluation | Staging / Hardened Defense | Enterprise Production Target |

---

## 3. Directory Layout

- [`deploy/aws/`](./aws): Contains the per-host Docker Compose configurations, PostgreSQL replication scripts, Nginx configurations, and migration tools for the 6-host EC2 topology.
- [`deploy/aws-ec2/`](./aws-ec2): Comprehensive deployment runbook, health-check matrices, and failover runbooks for AWS EC2.
- [`infra/aws/`](../infra/aws): CloudFormation/JSON infrastructure specifications for ECR repositories, ECS task definitions, ECS services, IAM roles, and RDS Multi-AZ.

---

## 4. Quick Navigation & References

- **AWS EC2 Setup & Failover Runbook**: See [`deploy/aws-ec2/README.md`](./aws-ec2/README.md).
- **CI/CD & Automated ECS Deployment**: See [`docs/deployment/aws-ec2/15-CICD-ARCHITECTURE.md`](../docs/deployment/aws-ec2/15-CICD-ARCHITECTURE.md).
- **SQLite to PostgreSQL Migration**: See [`deploy/aws/migrations/sqlite_to_postgres.py`](./aws/migrations/sqlite_to_postgres.py).
