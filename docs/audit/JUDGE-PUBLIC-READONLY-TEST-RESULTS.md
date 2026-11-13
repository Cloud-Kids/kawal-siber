# JUDGE PUBLIC READ-ONLY — Test Results

**Date:** 2026-11-13 — run in WSL Ubuntu 24.04 venv, `KAWAL_JUDGE_MODE=true`.

## Suite: `backend/tests/test_judge_mode.py` — 38/38 PASSED

### Positive (allowed GETs — 13 routes)
`/health`, `/assets`, `/scan-scopes`, `/scans`, `/incidents`,
`/monitoring/statistics`, `/security-events`, `/security-alerts`,
`/web-targets`, `/web-assessments`, `/web-findings`, `/reports`,
`/ai/health`, `/incident-intelligence/overview` → all 200/404 (404 only when table empty).

### Negative — writes denied (17 cases, all 403)
POST `/assets`, POST `/assets/1/scans`, POST `/scan-scopes`, PATCH `/scan-scopes/1`,
POST/PATCH/DELETE `/incidents*`, POST/PATCH/DELETE `/web-targets*`,
POST/DELETE `/web-assessments*`, POST `/monitoring/pcap`, POST `/reports`,
POST `/incidents/1/triage`, PUT `/assets/1`, DELETE `/assets/1` → **403**.

### Negative — surface disabled
`/docs`, `/redoc`, `/openapi.json` → 403/404. Unknown `/api/v1/*` → 403/404.
`/api/v1/admin/*` → 403.

### Negative — traversal/IDOR
`/reports/..%2F..%2Fetc%2Fpasswd/download` → 403/404/422.
`/reports/abc123/download` (non-UUID) → **403**.

## Not yet executed (requires deployment approval)

- [ ] `demo-kawal-siber.smkcloud.web.id` opens without OTP (external browser)
- [ ] Production hostname still requires Access (302 challenge)
- [ ] Judge stack survives production `docker compose down`
- [ ] Rate limit actually throttles (nginx + app layer)
- [ ] Report download end-to-end on real judge.db
- [ ] No prod DB path reachable from judge container (mount inspection)

## Regression note
Existing suite unaffected: judge middleware is a no-op unless
`KAWAL_JUDGE_MODE=true`; prod compose does not set it.
