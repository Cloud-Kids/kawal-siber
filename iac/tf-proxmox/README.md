# tf-proxmox — KAWAL SIBER Proxmox VE Infrastructure (Scaffold)

> **Status: scaffold.** The AWS target (`../tf-aws`) is complete and validated.
> This folder is reserved for the Proxmox VE on-premises deployment and will be
> implemented next.

## Planned scope

Mirror the active single-instance topology
(`deploy/single-instance/compose.single-instance.yaml`: Nginx reverse
proxy + frontend + backend + worker on one host) on Proxmox VE using the
`bpg/proxmox` community provider:

| VM / LXC | Role | Planned resources |
| :--- | :--- | :--- |
| `ks-app-01` | Full stack (proxy + frontend + backend + worker) | VM or LXC, cloud-init, persistent storage |

Planned files (to be added):

```
tf-proxmox/
├── versions.tf          # bpg/proxmox provider pin
├── providers.tf         # Proxmox endpoint + API token (env vars)
├── variables.tf         # pm_api_url, node names, datastore, templates
├── vms.tf               # qemu/qemu-server VMs with cloud-init
├── lxcs.tf              # (optional) unprivileged LXC containers
├── network.tf           // SDN / Linux bridge / VLAN definitions
├── storage.tf           // directory / LVM-thin datastores
└── outputs.tf
```

## Notes for implementation

- Reuse the host-preparation logic from `iac/tf-aws/templates/ec2-user-data.sh.tftpl`
  (Docker Engine + Compose plugin + `/opt/kawal-siber` directory layout).
- Deploy the application with `deploy/single-instance/compose.single-instance.yaml`.
- Secrets must be injected via Proxmox secrets / environment — never commit them.
