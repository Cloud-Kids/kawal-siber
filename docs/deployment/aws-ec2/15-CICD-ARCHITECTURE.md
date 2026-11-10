# 15. CI/CD Architecture & Automated Deployment Pipeline

## 1. Overview & Architecture Principles

The **KAWAL SIBER CI/CD Pipeline** automates the build, validation, image publishing, database migration, and rolling deployment of all system components onto an **AWS ECS on EC2 Multi-AZ Cluster** in `ap-southeast-1`.

```
  DEVELOPER WORKSTATION
          │
          ▼ git push / pull_request
┌────────────────────────────────────────────────────────┐
│ GITHUB ACTIONS CI/CD PIPELINE                          │
│                                                        │
│  [ Job 1: CI Testing & Quality Gate ]                  │
│  ├── Backend Pytest (129 tests)                        │
│  ├── Worker Pytest (22 tests)                          │
│  ├── Phase 6 Acceptance Suite (25 tests on temp DB)    │
│  ├── Frontend Type-Check (tsc --noEmit)                │
│  ├── Next.js 15 Standalone Build                       │
│  └── Dependency & Secret Scanning (Gitleaks, Pip-Audit)│
│                                                        │
│  [ Job 2: Secure AWS OIDC Authentication ]             │
│  └── Short-lived token exchange with AWS IAM Role      │
│                                                        │
│  [ Job 3: Amazon ECR Image Push ]                      │
│  ├── Tag: sha-<commit_sha> (IMMUTABLE)                 │
│  └── Security vulnerability scanning on push           │
│                                                        │
│  [ Job 4: Dedicated One-Off DB Migration Task ]        │
│  └── Standalone ECS task: alembic upgrade head         │
│                                                        │
│  [ Job 5: Multi-AZ ECS Rolling Deployment ]            │
│  ├── ECS Service Circuit Breaker with Auto-Rollback    │
│  ├── minimumHealthyPercent: 100, maximumPercent: 200   │
│  └── Task placement spread across 2+ AZs & instances   │
│                                                        │
│  [ Job 6: Post-Deployment Smoke Verification ]         │
│  └── Health endpoints, API status, UI dashboard probe  │
└────────────────────────────────────────────────────────┘
          │
          ▼ AWS Cloud Infrastructure (ap-southeast-1)
┌────────────────────────────────────────────────────────┐
│ AWS APPLICATION LOAD BALANCER (Multi-AZ Public Ingress)│
│   ├── Target Group: Frontend (Port 3000)               │
│   └── Target Group: Backend (Port 8000)                │
│                                                        │
│ AMAZON ECS ON EC2 CLUSTER                              │
│   ├── Frontend Service (desiredCount = 2, Multi-AZ)    │
│   ├── Backend Service (desiredCount = 2, Multi-AZ)     │
│   ├── Worker Service (desiredCount = 2, Multi-AZ)      │
│   └── Tools Agent Service (desiredCount = 2, Multi-AZ) │
│                                                        │
│ AMAZON RDS POSTGRESQL (Multi-AZ HA Persistence)        │
└────────────────────────────────────────────────────────┘
```

---

## 2. Security Boundaries & Zero-Trust Guarantees

1. **Zero Long-Lived AWS Keys**: No static `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` are stored in GitHub Secrets or images. Authentication uses OIDC tokens issued by GitHub's STS endpoint.
2. **Immutable ECR Image Tags**: Every production deployment is tagged with its full Git commit SHA (`sha-abc1234`). Overwriting release tags is blocked at the ECR registry policy level.
3. **Database Migration Isolation**: Database migrations are strictly excluded from container startup scripts. They run once as a dedicated, serialized ECS task before any service begins rolling updates.
4. **Local SQLite Development Database Untouched**: The primary local development database (`storage/kawal_siber.db`) is strictly excluded from Docker build contexts and CI test runs.

