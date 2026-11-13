# KAWAL SIBER — Single-EC2 Terraform (AWS Academy Learner Lab)

Terraform provisions **exactly two managed AWS resources**:

| Resource | Purpose |
| :--- | :--- |
| `aws_security_group` | Network access control (SSH + web only) |
| `aws_instance` | One Ubuntu 24.04 LTS EC2 host running the full stack via Docker Compose |

**No other AWS services are created**: no VPC, subnets, IGW, NAT, ALB, ECS,
ECR, RDS, S3, IAM, KMS, SNS, CloudWatch, Secrets Manager, Lambda, or
Auto Scaling. The VPC and subnet are **existing** Learner Lab resources
(reused via data sources). Docker Compose runs the application
(`deploy/single-instance/compose.single-instance.yaml`).

---

## Architecture

```
Internet ──► [AWS Security Group: 22 admin / 80,443 web]
                │
                ▼
        ┌───────────────────────────────┐
        │  EC2 · Ubuntu 24.04 LTS       │
        │  r6i.large (2 vCPU / 16 GiB)  │
        │  100 GiB gp3 root (encrypted) │
        │                               │
        │  Docker Compose:              │
        │   nginx (80/443) ──► frontend │
        │                    └─► backend ──► worker
        │   SQLite + reports on host    │
        │   /opt/kawal-siber/{data,storage}│
        └───────────────────────────────┘
```

Internal ports **3000, 8000, 5432, 6379, 9100, 11434 are never exposed** —
only the containerized Nginx reverse proxy publishes 80/443.

---

## Prerequisites

- Windows machine with **Terraform CLI >= 1.6** and **AWS CLI v2**
- An **AWS Academy Learner Lab** session (temporary credentials)
- An existing **EC2 key pair** in your chosen region (or create one — Step 7)

---

## AWS Academy Temporary Credentials — CRITICAL

Learner Lab credentials are **temporary** and expire when the lab session
ends. You need **all three** values:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_SESSION_TOKEN`

### Where to get them

1. Start your Learner Lab at `https://www.learnerlab.labs.skillsforit.com`
   (or your institution's AWS Academy portal).
2. Open **AWS Details** → copy the three values under
   *AWS Command Line Interface (CLI)* or *Option 1: Set AWS environment variables*.

### How to supply them (PowerShell — Windows)

```powershell
$env:AWS_ACCESS_KEY_ID     = "ASIA..."
$env:AWS_SECRET_ACCESS_KEY = "..."
$env:AWS_SESSION_TOKEN     = "IQoJb3JpZ2luX2Vj..."
$env:AWS_DEFAULT_REGION    = "us-east-1"
```

Or persist them in an AWS CLI profile (`aws configure --profile learner-lab`)
and export `AWS_PROFILE=learner-lab` before running Terraform.

> **NEVER** put these values in `terraform.tfvars`, `user_data`, the Git
> repository, Terraform outputs, README examples, or GitHub Actions secrets.
> They are temporary — refresh them every time you start a new Learner Lab
> session.

### Verify credentials before planning

```powershell
aws sts get-caller-identity
```

Expected output shows your `Account`, `Arn`, and `UserId`. If this fails,
fix credentials before continuing — do not proceed to `terraform plan`.

---

## Step-by-Step Deployment Procedure

### STEP 1 — Start AWS Academy Learner Lab
Log in and click **Start Lab**. Wait until the session timer begins.

### STEP 2 — Obtain temporary credentials
AWS Details → copy `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
`AWS_SESSION_TOKEN`.

### STEP 3 — Install Terraform & AWS CLI on Windows
- Terraform: <https://developer.hashicorp.com/terraform/install> (or
  `winget install Hashicorp.Terraform` / `choco install terraform`)
- AWS CLI v2: <https://aws.amazon.com/cli/> (`winget install Amazon.AWSCLI`)

Verify:

```powershell
terraform version   # >= 1.6
aws --version       # v2.x
```

### STEP 4 — Set credential environment variables
Run the PowerShell block from *AWS Academy Temporary Credentials* above in
the terminal session you will use for Terraform.

### STEP 5 — Verify identity

```powershell
aws sts get-caller-identity
```

**Troubleshooting:** `Unable to locate credentials` → env vars not set in
this shell. `InvalidClientTokenId` / `ExpiredToken` → lab session ended or
values copied incompletely; restart the lab and re-copy all three values.

### STEP 6 — Identify Region, VPC ID and Subnet ID

- **Region**: pick the region shown in your Learner Lab console (commonly
  `us-east-1`). All resources must be in this one region.
- **VPC ID**: AWS Console → **VPC** → *Your VPCs* → copy the `vpc-xxxxxxxx`
  of the default VPC.
- **Subnet ID**: VPC → **Subnets** → pick a **public** subnet (the one whose
  route table has `0.0.0.0/0 → igw-...` and *Auto-assign public IPv4* = Yes).
  Copy its `subnet-yyyyyyyy` ID.

> Terraform validates that the subnet belongs to the VPC and auto-assigns
> public IPs. It will **fail fast** with a clear error if the IDs mismatch —
> it never creates network infrastructure.

### STEP 7 — Create an EC2 Key Pair (if none exists)

AWS Console → **EC2** → *Key Pairs* → **Create key pair**:
- Name: `kawal-siber-key` (or your choice)
- Type: RSA, Format: `.pem`
- Download the `.pem` — it is shown **only once**.

Store it securely, e.g. `%USERPROFILE%\.ssh\kawal-siber-key.pem`, and restrict
permissions (icacls or `chmod 400` under WSL/Git Bash). **Never commit the
`.pem`** — `*.pem` is git-ignored in this repo.

### STEP 8 — Securely store the private key
Keep the `.pem` outside the repository. You will need it for SSH and for the
`ssh_command` Terraform output.

### STEP 9 — Create terraform.tfvars

```powershell
cd iac\tf-aws
copy terraform.tfvars.example terraform.tfvars
```

### STEP 10 — Fill in terraform.tfvars

| Variable | Value | Notes |
| :--- | :--- | :--- |
| `aws_region` | e.g. `us-east-1` | Must match VPC/subnet/key-pair region |
| `instance_type` | `r6i.large` | **Recommended default.** If Learner Lab rejects it, use `r5.large`, `r5a.large`, `m6i.large`, `t3.xlarge`, etc. |
| `key_name` | your key pair name | From Step 7 |
| `vpc_id` | `vpc-...` | From Step 6 |
| `subnet_id` | `subnet-...` | Public subnet from Step 6 |
| `admin_cidr` | `YOUR_IP/32` | Get via `curl https://checkip.amazonaws.com` — **never `0.0.0.0/0`** |
| `web_allowed_cidrs` | `["YOUR_IP/32"]` | Same restricted CIDR for initial testing |
| `root_volume_size` | `100` | GiB, gp3 |

No passwords or API secrets belong in this file.

### STEP 11 — Format, init, validate, plan

```powershell
terraform fmt -check
terraform init
terraform validate
terraform plan
```

### STEP 12 — Inspect the plan

Expected managed resource additions — **exactly two**:

```
Plan: 2 to add, 0 to change, 0 to destroy.
+ aws_security_group.kawal_siber
+ aws_instance.kawal_siber
```

Data sources only *read*: the Ubuntu 24.04 AMI, your VPC, your subnet.

> **If `terraform plan` fails** with `InvalidInstanceType`, `Unsupported`, or
> `not authorized`, the Learner Lab does not permit `r6i.large`. Change
> `instance_type` in `terraform.tfvars` to an allowed `.large`/`.xlarge`
> type and re-plan. `terraform validate` success does **not** prove the lab
> account can launch the instance — only `plan`/`apply` does.

### STEP 13 — Apply

```powershell
terraform apply
```

Type `yes` when prompted. Expect ~1–3 minutes for instance launch.

### STEP 14 — Capture outputs

```powershell
terraform output
```

Note `public_ip`, `ssh_command`, and `application_url`.

### STEP 15 — SSH into the instance

```powershell
ssh -i "$env:USERPROFILE\.ssh\kawal-siber-key.pem" ubuntu@<public_ip>
```

(Use the `ssh_command` output as reference; replace the key path.)

### STEP 16 — Verify Docker bootstrap & auto-deploy

The `user_data` script logs to `/var/log/kawal-siber-bootstrap.log`.

**Default behavior (`app_deploy_enabled = true`)**: cloud-init installs
Docker Engine + Compose plugin, clones the repo into
`/opt/kawal-siber/app` (with `--recurse-submodules`), creates the storage
directories, and runs `docker compose -f compose.single-instance.yaml
-p kawal-siber up -d --build` automatically. First image build on a
2 vCPU instance takes ~10–20 minutes.

Verify:

```bash
sudo docker version
sudo docker compose version
systemctl is-enabled docker   # expected: enabled
docker ps                     # reverse-proxy/frontend/backend/worker
sudo tail -50 /var/log/kawal-siber-bootstrap.log
ls -la /opt/kawal-siber/      # app, data, backups, storage/reports
```

If Docker is missing, check the bootstrap log — most failures are apt
mirror timeouts; re-run the apt/docker steps manually.

#### Git authentication for the private repo

The repo is **private**, so cloud-init needs credentials to clone it.
Two options — pick ONE:

**Option A — fine-grained PAT (recommended; orgs may disable Deploy Keys)**

1. GitHub → Settings → Developer settings → **Fine-grained tokens** →
   Generate. Resource owner: `Cloud-Kids`. Repository access: **Only
   select repositories → `kawal-siber`**. Permissions: **Contents:
   Read-only**. Expiration: your choice.
2. Supply it to Terraform — do NOT put it in a committed file:

   ```powershell
   $env:TF_VAR_git_access_token = "github_pat_..."
   ```

   or add `git_access_token = "github_pat_..."` to your local
   `terraform.tfvars` (gitignored — verify it is NOT tracked).

   The token is injected into user-data and stored in Terraform state.
   On the instance it lands in `/home/ubuntu/.git-credentials`
   (mode 600) via git's credential helper. Treat it as a secret:
   revoke/rotate the PAT when the lab instance is destroyed.

**Option B — SSH deploy key**

Leave `git_access_token` empty. Terraform generates an ED25519 keypair;
`terraform output git_deploy_public_key` gives you the public key — add
it once in GitHub → repo **Settings → Deploy keys** (read-only). This
only works if your org allows deploy keys (Cloud-Kids currently does
not — prefer Option A).

#### Manual fallback (app_deploy_enabled = false)

If you disabled auto-deploy, run these steps yourself:

```bash
cd /opt/kawal-siber/app
sudo chown -R ubuntu:ubuntu /opt/kawal-siber
git clone https://github.com/Cloud-Kids/kawal-siber.git .
git submodule update --init --recursive   # public submodules, no auth needed

cd /opt/kawal-siber/app/deploy/single-instance
docker compose -f compose.single-instance.yaml config    # validate
docker compose -f compose.single-instance.yaml build
docker compose -f compose.single-instance.yaml up -d
```

> **Do NOT** embed a GitHub PAT in the remote URL. If cloning manually
> on a private repo, use `git clone https://github.com/...` with a
> credential helper, or export `GIT_ASKPASS`.

### STEP 17 — Verify all components

```bash
# Reverse proxy health
curl -f http://localhost/healthz
# Backend API health (through proxy)
curl -f http://localhost/api/v1/health
# Direct container checks
docker compose -f deploy/single-instance/compose.single-instance.yaml ps
# Expected services: reverse-proxy, frontend, backend, worker — all healthy
```

### STEP 18 — Open the application

Browse to `http://<public_ip>` (the `application_url` output). Access is
restricted to `web_allowed_cidrs` — if you set your `/32`, only your IP can
reach it.

**HTTPS**: not configured by Terraform. For production, run Caddy or Nginx
TLS termination on the host with a real domain A record → `public_ip`,
then issue a certificate (e.g. Let's Encrypt). Do not claim HTTPS until the
domain and cert are verified.

---

## Routine Operations

```bash
# Status / logs / restart
docker compose -f deploy/single-instance/compose.single-instance.yaml ps
docker compose -f deploy/single-instance/compose.single-instance.yaml logs -f backend
docker compose -f deploy/single-instance/compose.single-instance.yaml restart

# Update application (NEVER down -v)
cd /opt/kawal-siber/app
git pull origin main && git submodule update --init --recursive
docker compose -f deploy/single-instance/compose.single-instance.yaml build
docker compose -f deploy/single-instance/compose.single-instance.yaml up -d
```

Full runbook: [`deploy/single-instance/README.md`](../../deploy/single-instance/README.md).

## Backup & Restore

- **Database**: `sqlite3 storage/kawal_siber.db ".backup 'storage/backups/kawal_siber_$(date +%F).db'"`
- **Reports**: copy `storage/reports/` off-host.
- **Whole host**: Learner Lab instances are ephemeral — snapshot important
  data off the instance regularly.

## Destroy — DATA LOSS WARNING

`terraform destroy` terminates the EC2 instance. With
`delete_on_termination = true` (default) the **root EBS volume and all
data on it are permanently deleted**. Back up `storage/` first, or set
`delete_on_termination = false` if you want the volume to survive.

## Cost & Quota Notes (Learner Lab)

- Instances accrue credits against your lab time quota; stop/terminate when
  done (`terraform destroy` or EC2 console → terminate).
- Instance types are whitelisted — `r6i.large` may be denied; fall back per
  `instance_type` docs in `variables.tf`.
- Learner Lab credentials expire — re-export env vars each session.

## Proxmox Portability

The same Docker Compose stack runs unchanged on a Proxmox QEMU VM
(100% parity) or unprivileged LXC (`features: nesting=1,keyctl=1`).
The future `iac/tf-proxmox/` root will provision that target; keep this
root AWS-only.

## CI/CD Note

GitHub Actions CI (`.github/workflows/ci.yml`) is AWS-independent. Optional
single-EC2 CD via a self-hosted runner is possible but **requires explicit
security review** (self-hosted runners must never execute untrusted
`pull_request`/fork workflows on the production host). Keep deployment
manual until then.
