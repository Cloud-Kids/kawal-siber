# deploy/proxmox — Proxmox VE Deployment (Future)

Placeholder for the Proxmox VE on-premises deployment target.

- Provisioning scaffold: [`iac/tf-proxmox/`](../../iac/tf-proxmox/)
- Application stack (shared with AWS EC2):
  [`deploy/single-instance/compose.single-instance.yaml`](../single-instance/compose.single-instance.yaml)
- Operational runbook: [`deploy/single-instance/README.md`](../single-instance/README.md)
  (see §10 "Proxmox Portability" for VM vs LXC guidance)

The same Docker Compose stack runs unchanged on a Proxmox QEMU VM
(100% parity with EC2) or an unprivileged LXC container
(`features: nesting=1,keyctl=1`, ext4 storage backend recommended).
