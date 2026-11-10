# 16. GitHub Actions Setup & Repository Configuration

## 1. GitHub Environment Configuration

1. In your GitHub repository, navigate to **Settings** > **Environments**.
2. Click **New environment** and enter the name: `production`.
3. Configure the following environment protection rules:
   - **Required reviewers**: Designate at least one Principal Security Architect or Lead DevOps Engineer to approve production deployments.
   - **Deployment branches**: Restrict deployments to the `main` branch only.

---

## 2. GitHub Secrets Configuration

Navigate to **Settings** > **Secrets and variables** > **Actions** > **Environment secrets** (for `production`):

| Secret Name | Description | Example / Format |
| :--- | :--- | :--- |
| `AWS_DEPLOY_ROLE_ARN` | The ARN of the IAM Role assumed via OIDC | `arn:aws:iam::123456789012:role/kawal-siber-github-deployer-role` |
| `ECS_PRIVATE_SUBNETS` | Private subnet IDs for migration tasks | `["subnet-0aaa1111private1a", "subnet-0bbb2222private1b"]` |
| `ECS_TASK_SECURITY_GROUPS` | Security Group ID for ECS migration tasks | `["sg-0123456789backend"]` |

> [!CAUTION]
> Do **NOT** configure static `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY`. The pipeline strictly uses OpenID Connect (OIDC).

---

## 3. GitHub Repository Variables Configuration

Navigate to **Settings** > **Secrets and variables** > **Actions** > **Variables**:

| Variable Name | Description | Default Value |
| :--- | :--- | :--- |
| `AWS_REGION` | Target AWS region | `ap-southeast-1` |
| `ECS_CLUSTER_NAME` | ECS Cluster name | `kawal-siber-prod` |
| `ECS_MIGRATION_TASK_DEF` | Task definition family for migrations | `kawal-siber-migration` |
| `PRODUCTION_APP_URL` | Public endpoint for post-deploy smoke tests | `https://kawal-siber.mil.id` |

---

## 4. Branch Protection Rules

Under **Settings** > **Branches**, enable protection for `main`:
- [x] **Require a pull request before merging**
- [x] **Require status checks to pass before merging**:
  - `Backend, Worker & Acceptance Tests`
  - `Frontend Type-Check & Build`
  - `Dependency Audit & Secret Scanning`
  - `Dockerfile Build Validation`
- [x] **Require branches to be up to date before merging**
- [x] **Do not allow bypassing the above settings**
