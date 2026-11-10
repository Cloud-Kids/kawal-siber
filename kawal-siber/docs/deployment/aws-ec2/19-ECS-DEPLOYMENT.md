# 19. AWS ECS on EC2 Automated Deployment

## 1. Multi-AZ Service Topology

The ECS cluster (`kawal-siber-prod`) executes container instances spread across at least two Availability Zones (`ap-southeast-1a` and `ap-southeast-1b`).

### Service Architecture Specifications:

| ECS Service | Desired Replicas | Placement Strategy | Placement Constraint | Health Check Grace Period |
| :--- | :--- | :--- | :--- | :--- |
| **`kawal-siber-frontend-service`** | 2 | `spread(az)`, `spread(instanceId)` | `distinctInstance` | 60 seconds |
| **`kawal-siber-backend-service`** | 2 | `spread(az)`, `spread(instanceId)` | `distinctInstance` | 60 seconds |
| **`kawal-siber-worker-service`** | 2 | `spread(az)`, `spread(instanceId)` | `distinctInstance` | N/A (Internal queue) |
| **`kawal-siber-tools-agent-service`**| 2 | `spread(az)`, `spread(instanceId)` | `distinctInstance` | 30 seconds |

---

## 2. Dedicated One-Off Database Migration Task

To prevent concurrent migration conflicts, migrations run as a standalone task before services deploy:

```bash
# Executed by GitHub Actions CD before service rolling updates:
TASK_ARN=$(aws ecs run-task \
  --cluster kawal-siber-prod \
  --task-definition kawal-siber-migration \
  --launch-type EC2 \
  --query "tasks[0].taskArn" \
  --output text)

# Wait for completion:
aws ecs wait tasks-stopped --cluster kawal-siber-prod --tasks "$TASK_ARN"

# Verify exit code:
EXIT_CODE=$(aws ecs describe-tasks \
  --cluster kawal-siber-prod \
  --tasks "$TASK_ARN" \
  --query "tasks[0].containers[0].exitCode" \
  --output text)

if [ "$EXIT_CODE" != "0" ]; then
  echo "Migration failed! Halting deployment."
  exit 1
fi
```

---

## 3. Rolling Update & Capacity Surge

- **`minimumHealthyPercent: 100`**: At least 2 healthy replicas must remain active and serving traffic at all times during deployment.
- **`maximumPercent: 200`**: Allows up to 4 replicas to run concurrently while new tasks are launched and evaluated.
- **Circuit Breaker**: `enable: true`, `rollback: true`. If new tasks fail health checks or crash repeatedly, ECS automatically reverts to the previous task definition revision.
