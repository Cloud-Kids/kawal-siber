# JUDGE PUBLIC READ-ONLY — Pre-Deployment Readiness Audit

**Date:** 2026-11-13 · **Branch:** `feat/judge-public-readonly`
**Scope:** local validation only — no push/deploy/Cloudflare/AWS changes.

## A. Database Startup Compatibility (P0) — PASS

Three startup write paths were found and fixed:

| Path | Issue | Fix |
|---|---|---|
| `PRAGMA journal_mode=WAL` on every connect | write attempt → fails on ro file | skipped when `KAWAL_JUDGE_MODE=true` (`database.py`) |
| `Base.metadata.create_all` in lifespan | write if tables missing | skipped in judge mode (`main.py`) |
| Stale-job reaper `UPDATE pcap_analyses` | write at startup | skipped in judge mode (`main.py`) |

Integration test (WSL, real uvicorn):
- judge.db built via `create_all`, `chmod 444`, `DATABASE_URL=sqlite:////tmp/judgetest/judge.db`
- `KAWAL_JUDGE_MODE=true` → startup **complete**, no errors
- `GET /api/v1/health` → 200; `GET /api/v1/monitoring/statistics` → 200 JSON
- `POST /api/v1/assets` → **403**
- `GET /docs` → **403**
- **SHA-256 identical before/after** (`62fedaaa…5688e`) — zero DB writes

Production behavior unchanged: all gates keyed on `KAWAL_JUDGE_MODE`, unset in prod.

## B. Frontend Production Build

- `tsc --noEmit`: PASS (earlier)
- `NEXT_PUBLIC_JUDGE_MODE=true npm run build`: see test-results section below
- Banner component `JudgeMode.tsx` renders only when env flag true; client
  fetch wrapper rejects non-GET/HEAD/OPTIONS. Backend 403 remains authoritative.

## C. Docker Compose Static Validation — PASS

`docker compose -f deploy/judge-demo/compose.judge.yaml config` → **VALID**

- `judge-proxy`: `127.0.0.1:8081:8081` loopback-only; 128M/0.25cpu
- `judge-backend`: no published ports; `storage/judge:/data:ro`; 512M/0.5cpu
- `judge-frontend`: no published ports; 512M/0.5cpu; build arg `NEXT_PUBLIC_JUDGE_MODE=true`
- No docker socket, no `privileged`, no prod DB mount, separate `judge_net`
- nginx: `server_name demo-kawal-siber.smkcloud.web.id`, `default_server` → 444,
  `limit_req_zone` 10r/s, `/docs|redoc|openapi.json` → 403, `noindex` headers

## D. Cloudflare Configuration Readiness (instructions only — NOT applied)

Prerequisites before any change (requires separate approval + CF token):

1. Verify NO Access application covers `demo-kawal-siber.smkcloud.web.id`
   (Access → Applications). If one exists → delete or scope it away FIRST.
2. Tunnel `kawal-siber` → Public Hostnames → Add:
   - Hostname: `demo-kawal-siber.smkcloud.web.id`
   - Service: `http://localhost:8081` (cloudflared runs on HOST — correct)
3. DNS: CNAME `demo-kawal-siber` → `<tunnel-id>.cfargotunnel.com` (proxied).
   Do NOT touch `kawal-siber` records or the Access app.
4. Optional: WAF rate-limit rule on the demo hostname.
5. Rollback: delete the public hostname route + DNS record; judge stack
   `docker compose -p kawal-judge down -v`.

## E. Test Results (actual)

| Suite | Result |
|---|---|
| Judge mode tests | 45/45 PASS |
| Full backend suite | 183 passed, 1 skipped, 0 failed |
| Frontend tsc | PASS |
| Frontend `next build` (judge flag) | **PASS** (after JudgeGuard client-component fix) |
| Compose config | VALID |
| Read-only DB integration | PASS (checksum unchanged) |

## F. Resource Estimates

EC2 r6i.large: ~14Gi RAM free, 90G disk free. Judge stack limits total
~1.1Gi RAM / 1.25 cpu — comfortable headroom alongside prod (~600Mi used).

## G. Remaining Risks / Deployment Prerequisites

1. `init_db` no-op verified for empty-schema snapshot; prod snapshot has all
   tables — re-verify at deploy with real judge.db.
2. judge.db must be rebuilt per demo if prod data changes; document refresh.
3. Report files must be copied into `storage/judge/reports/` (script arg 3).
4. Rate limit is per-IP at nginx; cloudflared egress may aggregate IPs —
   monitor 429s during demo.
5. Frontend operational buttons: hidden via env-gated UI + fetch guard;
   backend 403 is the real enforcement — verified.
6. No Access app must exist for demo hostname — verify in CF dashboard
   before exposing (cannot be checked without token).

## H. Rollback

See `JUDGE-PUBLIC-READONLY-ROLLBACK.md` — additive-only; remove tunnel
hostname route, `compose down -v`, delete `storage/judge/`. Production
untouched at every level.
