# 21. Release Verification & Failure Testing Matrix

## 1. Post-Deployment Smoke Verification Checklist

Immediately following deployment completion, the automated CD workflow executes the following verification probes:

| Component | Target URL / Probe | Expected Status | Verification Objective |
| :--- | :--- | :--- | :--- |
| **Public ALB** | `https://kawal-siber.mil.id/` | HTTP 200 | TLS termination valid; frontend HTML delivered |
| **Backend API** | `https://kawal-siber.mil.id/api/v1/health` | HTTP 200 (`{"status":"healthy"}`) | API alive; RDS database connection pool operational |
| **Worker Queue** | CloudWatch Metric `OldestPendingJobAge` | < 60s | Workers actively claiming and processing jobs |
| **Tools Agent** | `POST http://tools.kawal-siber.internal:9000/health` | HTTP 200 | Nmap binary operational; scope guard active |
| **Static Assets** | `/_next/static/*` | HTTP 200 / 304 | Next.js standalone static files cached and served |

---

## 2. Failure & Rollback Test Scenarios Matrix

The following scenarios are cataloged for operational readiness testing:

| Test Scenario | Target Tier | Verification Method | Status | Disclosed Verification Note |
| :--- | :--- | :--- | :--- | :--- |
| **Backend Image Fails to Start** | Backend ECS | Deploy invalid config; verify circuit breaker rolls back to prior revision | **NOT RUN** | Live AWS ECS cluster not provisioned in local dev environment. |
| **Frontend Image Returns 500** | Frontend ECS | Introduce fatal error; verify ALB target group fails health check and routes to healthy task | **NOT RUN** | Live AWS ALB target group required. |
| **Worker Exits During Scan** | Worker Pool | Kill task mid-execution; verify sibling worker reclaims stale job after 10m lease | **NOT RUN** | Multi-task PostgreSQL worker pool required. |
| **Database Migration Fails** | RDS / Alembic | Execute bad migration; verify migration task fails and halts service updates | **NOT RUN** | Tested in isolated acceptance suite; live RDS not provisioned. |
| **ECR Image Pull Fails** | ECR / ECS | Introduce IAM role restriction; verify deployment circuit breaker rolls back | **NOT RUN** | Live AWS ECR IAM role required. |
| **ECS Circuit Breaker Trigger** | ECS Cluster | Deploy unstartable container; verify automated rollback event emitted | **NOT RUN** | CloudWatch deployment metrics required. |

> [!NOTE]
> All live cloud failure scenarios are marked **`NOT RUN`** because the AWS ECS Multi-AZ production cluster is not yet provisioned in this local development environment. Never claim pass status without actual live cloud runtime evidence.
