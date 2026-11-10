# AWS Application Load Balancer (ALB) Multi-AZ Configuration

## 1. Architecture Overview

The public ingress layer is an **AWS Application Load Balancer** provisioned across at least two Availability Zones (`ap-southeast-1a` and `ap-southeast-1b`).

```
                    INTERNET (Defense Operators)
                                │
                    [ AWS Application Load Balancer ]
                    - Scheme: Internet-facing
                    - Subnets: subnet-pub-1a, subnet-pub-1b
                    - TLS: ACM Certificate (TLS 1.3 / 1.2)
                                │
        ┌───────────────────────┴───────────────────────┐
        │                                               │
   Path: /api/*                                   Default Path: /*
        ▼                                               ▼
[ Target Group: Backend ]                       [ Target Group: Frontend ]
- Port: 8000 (HTTP)                             - Port: 3000 (HTTP)
- Health: /api/v1/health                        - Health: /
- Target Type: ip (awsvpc)                      - Target Type: ip (awsvpc)
- Algorithm: least_outstanding_requests         - Algorithm: round_robin
```

---

## 2. Target Group Specifications

### 2.1 Backend Target Group (`tg-kawal-backend`)
- **Protocol / Port**: HTTP / 8000
- **Target Type**: `ip` (supporting ECS `awsvpc` network mode)
- **VPC**: `vpc-0123456789kawal` (`10.0.0.0/16`)
- **Health Check Path**: `/api/v1/health`
- **Health Check Interval**: 15 seconds
- **Health Check Timeout**: 5 seconds
- **Healthy Threshold Count**: 2 consecutive passes
- **Unhealthy Threshold Count**: 3 consecutive failures
- **Deregistration Delay**: 30 seconds (connection draining during rolling updates)

### 2.2 Frontend Target Group (`tg-kawal-frontend`)
- **Protocol / Port**: HTTP / 3000
- **Target Type**: `ip`
- **Health Check Path**: `/`
- **Health Check Interval**: 15 seconds
- **Health Check Timeout**: 5 seconds
- **Healthy Threshold**: 2
- **Unhealthy Threshold**: 3
- **Deregistration Delay**: 30 seconds

---

## 3. ALB Listener Rules

1. **HTTPS Listener (Port 443)**:
   - Default Action: Forward to `tg-kawal-frontend`.
   - SSL Policy: `ELBSecurityPolicy-TLS13-1-2-2021-06`.
   - Certificate: `arn:aws:acm:ap-southeast-1:123456789012:certificate/abcdef-1234`.
   - **Rule 1 (Path `/api/*`)**:
     - Priority: 10
     - Action: Forward to `tg-kawal-backend`.
2. **HTTP Listener (Port 80)**:
   - Default Action: Redirect to HTTPS port 443 with status code `HTTP_301`.
