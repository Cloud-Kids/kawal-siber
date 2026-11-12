# KAWAL SIBER — Infrastructure as Code (IaC)

Terraform infrastructure definitions for all KAWAL SIBER deployment targets.

```
iac/
├── README.md            # This file
├── tf-aws/              # AWS: ONE EC2 instance + ONE Security Group
└── tf-proxmox/          # Proxmox VE: future scaffold (see its README)
```

## tf-aws — Single-EC2 deployment (ACTIVE)

The finalized AWS architecture is a **single EC2 host** running the full
KAWAL SIBER stack via Docker Compose
(`deploy/single-instance/compose.single-instance.yaml`).

Terraform manages **exactly two resources**:

- `aws_security_group` — SSH (22) from admin CIDR; HTTP/HTTPS (80/443) from
  web-allowed CIDRs; unrestricted egress for apt/Docker/GitHub/cert issuance.
- `aws_instance` — Ubuntu Server 24.04 LTS, `r6i.large` default
  (overridable), 100 GiB gp3 encrypted root volume, `user_data` installs
  Docker Engine + Compose plugin.

**Explicitly NOT created**: VPC, subnets, IGW, NAT, ALB, ECS, ECR, RDS, S3,
IAM roles/profiles, KMS, SNS, CloudWatch, Secrets Manager, Lambda,
Auto Scaling — the existing Learner Lab VPC/subnet are reused via data
sources. Internal ports (3000/8000/5432/6379/9100/11434) are never exposed;
the containerized Nginx reverse proxy is the only public ingress.

See `tf-aws/README.md` for the full Learner Lab deployment runbook.

## tf-proxmox — Proxmox VE deployment (FUTURE)

Scaffold for the on-premises Proxmox VE target. See `tf-proxmox/README.md`.

## Legacy / Future Architecture

The previous multi-instance EC2 topology (`deploy/aws/`,
`deploy/aws-ec2/`), ECS Multi-AZ specifications (`infra/aws/`), and the
ECS-based CI/CD guides (`docs/deployment/aws-ec2/`) were **removed**
during the legacy infrastructure cleanup — the single-EC2 + Docker
Compose architecture above is the only active deployment path. A future
HA architecture may be designed separately as a roadmap item.
