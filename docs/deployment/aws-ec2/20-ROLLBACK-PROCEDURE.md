# 20. Production Rollback Procedure

## 1. Automated Circuit Breaker Rollback

If a newly deployed container fails health checks, crashes, or is unable to bind to the network within the grace period:
1. The **ECS Deployment Circuit Breaker** triggers automatically.
2. The deployment state transitions to `FAILED`.
3. ECS initiates an automated rollback to the last stable task definition revision (`revision - 1`).
4. The CloudWatch Alarm `kawal-siber-ecs-deployment-circuit-breaker-fired` alerts the DevOps team.

---

## 2. Operator-Controlled Manual Rollback (GitHub Actions)

If a logical defect or data integrity issue is discovered after deployment:

1. Navigate to **GitHub Actions** > **KAWAL SIBER — Production Service Rollback**.
2. Click **Run workflow**.
3. Select the affected service (e.g. `kawal-siber-backend-service`).
4. (Optional) Provide an explicit prior task revision (e.g. `kawal-siber-backend:24`). If omitted, the workflow automatically resolves and rolls back to `n - 1`.
5. Enter a mandatory **Rollback Reason** for audit records.
6. Click **Run workflow**.

---

## 3. Emergency AWS CLI Rollback Procedure

If GitHub Actions is unreachable, an authorized engineer can execute a direct rollback via AWS CLI:

```bash
# 1. Inspect current and prior task definition revisions
aws ecs describe-services \
  --cluster kawal-siber-prod \
  --services kawal-siber-backend-service \
  --query "services[0].taskDefinition"

# 2. Update service to target prior revision (e.g. revision 24)
aws ecs update-service \
  --cluster kawal-siber-prod \
  --service kawal-siber-backend-service \
  --task-definition kawal-siber-backend:24 \
  --force-new-deployment

# 3. Wait for service to reach steady state
aws ecs wait services-stable \
  --cluster kawal-siber-prod \
  --services kawal-siber-backend-service

# 4. Verify endpoint health
curl -s -f https://kawal-siber.mil.id/api/v1/health
```

