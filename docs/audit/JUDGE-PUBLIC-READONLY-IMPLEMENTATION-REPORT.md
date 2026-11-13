# JUDGE PUBLIC READ-ONLY — Implementation Report

**Date:** 2026-11-13
**Status:** IMPLEMENTED LOCALLY — deployment requires separate approval.

## Architecture

```
demo-kawal-siber.smkcloud.web.id  (public, NO Cloudflare Access)
  → cloudflared (existing tunnel, +1 public hostname → http://localhost:8081)
  → kawal-judge-proxy (nginx, 127.0.0.1:8081 only)
      ├─ /api/v1/* → judge-backend:8001  (KAWAL_JUDGE_MODE=true, judge.db :ro)
      └─ /         → judge-frontend:3001 (NEXT_PUBLIC_JUDGE_MODE=true build)
```

Production stack (`kawal-siber.*` → proxy:80 → frontend/backend/worker) is **untouched**.

## Files created/changed

| File | Change |
|---|---|
| `backend/app/judge_mode.py` | NEW — deny-by-default GET allowlist, method block, docs disable, rate limit, UUID report-download guard |
| `backend/app/main.py` | judge guard middleware + docs/openapi disabled when `KAWAL_JUDGE_MODE=true` |
| `backend/tests/test_judge_mode.py` | NEW — 30+ positive/negative cases |
| `deploy/judge-demo/compose.judge.yaml` | NEW — 3 services, resource limits, judge.db `:ro` mount |
| `deploy/judge-demo/judge-nginx.conf` | NEW — server_name demo-*, default_server 444, rate limit zone, noindex headers |
| `frontend/Dockerfile` | `ARG/ENV NEXT_PUBLIC_JUDGE_MODE` |
| `frontend/components/judge/JudgeMode.tsx` | NEW — banner + client fetch mutation block |
| `frontend/app/layout.tsx` | mount banner + guard |
| `scripts/build-judge-db.sh` | NEW — WAL-checkpointed `.backup` snapshot → sanitized `judge.db` mode 444 |

## Ports / containers

- `kawal-judge-proxy` → `127.0.0.1:8081` (host loopback only; cloudflared on host reaches it)
- `kawal-judge-backend` → internal `judge_net:8001` (not published)
- `kawal-judge-frontend` → internal `judge_net:3001` (not published)
- No new AWS Security Group rules — origin stays tunnel-only.

## Database isolation

- `storage/judge/judge.db` — separate file, built via SQLite `.backup` (consistent WAL checkpoint), `generated_by` relabelled `judge-demo`, chmod 444, mounted `:ro`.
- Judge backend has **no mount access** to `storage/kawal_siber.db`.

## Enforcement layers

1. **Nginx judge-proxy**: hostname allowlist, default_server 444, `/docs|redoc|openapi` 403, rate limit 10r/s.
2. **Backend judge_mode middleware**: non-GET → 403; non-allowlisted GET → 403; docs → 403; report download requires UUID; 120 req/min/IP.
3. **Frontend**: banner + fetch mutation block (UX layer only).

## Resource assessment (EC2 r6i.large)

- RAM: 15Gi total, ~915Mi used → judge stack ~250Mi limits headroom. Disk 90G free.
- Containers: proxy 128M/0.25cpu, backend 512M/0.5cpu, frontend 512M/0.5cpu.

## Remaining risks

- Allowlist completeness: new GET endpoints added later must be reviewed for judge mode.
- Sanitized DB still contains demo telemetry (IPs, findings) — intended, but review before deploy.
- Rate limit is in-memory per container — sufficient for demo.
