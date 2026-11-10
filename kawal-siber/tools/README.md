# KAWAL SIBER — Security Tools & External Integrations

## 1. Overview & Tool Ecosystem

KAWAL SIBER integrates a hardened layer of open-source security utilities to provide network discovery, intrusion detection, and web application security auditing:

```
  BACKEND API / ASYNC WORKER
              │
              │ Internal Authenticated HTTP REST (X-Agent-Key)
              ▼
  ┌────────────────────────────────────────────────────────┐
  │ KAWAL SIBER TOOLS AGENT (ks-tools-01 / Container)      │
  │                                                        │
  │  [ In-Container Scope & Policy Guard ]                 │
  │  ├── Re-validates target IPv4 against active CIDR      │
  │  └── Strictly blocks Loopback, Link-Local & Multicast  │
  │                                                        │
  │  [ Concurrency Throttling ]                            │
  │  └── asyncio.Semaphore(4) limits simultaneous jobs     │
  │                                                        │
  │  [ Executed Tool Engines ]                             │
  │  ├── 1. Nmap (Network Discovery & Port Scanner)        │
  │  ├── 2. Suricata (Network Intrusion Detection & PCAP)  │
  │  └── 3. Deep Eye (Web Security & Vulnerability Engine) │
  └────────────────────────────────────────────────────────┘
```

---

## 2. Integrated Security Tools Specifications

### 2.1 Nmap (Network Mapper)
- **Verified Version**: `Nmap 7.95` (Windows / Linux).
- **Execution Mode**: Non-privileged TCP connect scan (`nmap -sT -p <ports> -oX <xml> --open -n -T4 <target>`).
- **Policy**: Does not require root/administrator privileges; avoids aggressive scanning templates (`-T5` or intrusive NSE scripts) to maintain non-destructive operations.

### 2.2 Suricata (IDS / IPS Engine)
- **Verified Version**: `Suricata 7.0.7` / `7.0.8`.
- **Configuration**: Uses dedicated configuration file `storage/suricata.yaml` and rule sets in `storage/suricata/rules/`.
- **Telemetry Processing**: Ingests EVE JSON events (`eve.json`) with strict schema validation, alert severity mapping, and correlation with territorial assets.

### 2.3 Deep Eye Web Security Engine
- **Upstream Repository**: `https://github.com/zakirkun/deep-eye.git`
- **Pinned Commit**: `e4397d1`
- **Engine Version**: `1.4.0 (Hanzou)`
- **Local Hardening Patch**: A critical safety patch is applied in `modules/file_upload/upload_tester.py`. The original destructive shell upload tests are replaced with a safe stub to guarantee compliance with the hackathon's non-destructive assessment rules.
- **Profiles Supported**:
  - `PASSIVE`: Inspects HTTP security headers, cookies, TLS/SSL, CORS, CSP, and information disclosure (max 20 requests, 5.0 RPS).
  - `SAFE_LOCAL`: Non-destructive endpoint enumeration and reflection checks (max 50 requests, 2.0 RPS).

---

## 3. Tools Agent Microservice Architecture

In distributed and containerized deployments (such as AWS EC2 `ks-tools-01`), security tools are isolated inside a dedicated container image:

- **Source**: [`deploy/aws/ks-tools-01/agent/tools_agent.py`](../deploy/aws/ks-tools-01/agent/tools_agent.py)
- **Dockerfile**: [`deploy/aws/ks-tools-01/Dockerfile`](../deploy/aws/ks-tools-01/Dockerfile)
- **Listen Port**: `9000` (mapped to `9001` for `tools-agent-a` and `9002` for `tools-agent-b`).
- **Authentication**: All endpoints require the `X-Agent-Key` HTTP header.
- **Health Check**: `GET /health` returns engine availability and capacity metrics.

---

## 4. Scope Validation & Defense Safeguards

Every scan invocation must pass three layers of scope enforcement:
1. **Frontend / API Layer**: The target IP/URL must belong to an active, unexpired `ScanScope` or `WebTarget`.
2. **Worker Layer**: Re-evaluates CIDR boundaries before submitting the scan job.
3. **In-Container Tools Agent Layer**: The agent validates the IP address independently via Python's `ipaddress` module:
   - **Loopback Protection**: `127.0.0.0/8` is blocked.
   - **Cloud Metadata Protection**: `169.254.0.0/16` (including `169.254.169.254`) is strictly blocked.
   - **Multicast Protection**: `224.0.0.0/4` is blocked.
   - **CIDR Boundary**: Any IP outside the authorized CIDR raises `HTTP 403 Forbidden`.

---

## 5. Resource Constraints & Capacity

- **Concurrency Semaphore**: Limited to `MAX_CONCURRENT_SCANS=4` per container via `asyncio.Semaphore`.
- **CPU & Memory**: Recommended limits of `1.5 vCPU` and `1536 MB RAM` per agent container.
- **Temporary Storage**: Temporary scan XML files and PCAP dumps are isolated in unique temporary directories (`/tmp/ks_scan_*`) and purged immediately upon job completion.

