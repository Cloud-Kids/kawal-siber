# KAWAL SIBER — Deployment Guides

## Active deployment path

The **only active deployment architecture** is the single-instance Linux
host running Docker Compose:

- Canonical runbook: [`deploy/single-instance/README.md`](../../deploy/single-instance/README.md)
- Production Compose manifest: [`deploy/single-instance/compose.single-instance.yaml`](../../deploy/single-instance/compose.single-instance.yaml)
- Nginx ingress: [`deploy/single-instance/nginx.conf`](../../deploy/single-instance/nginx.conf)
- AWS provisioning (1 EC2 + 1 Security Group): [`iac/tf-aws/`](../../iac/tf-aws/)
- Proxmox target (scaffold): [`iac/tf-proxmox/`](../../iac/tf-proxmox/)

## Local development

`compose.yaml` at the repository root is the **local development
evaluation stack** (loopback-only port bindings, named volumes,
`SCAN_ENABLED=false`). It is not the production manifest.

## Continuous deployment (future)

A single-EC2 CD pipeline may be introduced later (e.g. SSH/rsync-based
or a hardened self-hosted runner). It requires explicit security design
first — a self-hosted runner must never execute untrusted
`pull_request`/fork workflows on the production host, SSH must never be
open to `0.0.0.0/0`, and long-lived AWS access keys should not be used.
Keep deployment manual until then.

## Historical note

The previous six-EC2 / ECS / ECR / ALB / RDS multi-service deployment
documentation was removed during the legacy infrastructure cleanup.
Historical engineering records remain under [`docs/reports/`](../reports/).
