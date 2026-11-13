# PRE-COMMIT SECURITY REVIEW — Judge Public Read-Only (Phase 3)

**Date:** 2026-11-13 · **Branch:** `feat/judge-public-readonly` · **Commit:** `c2e7ee2`
**Verdict:** SAFE TO COMMIT (local). Deployment still requires separate approval.

## A. GET Allowlist Audit

Allowlisted prefixes (`judge_mode.py`): health, assets, scan-scopes, scans,
incidents, incident-intelligence, monitoring, security-events, security-alerts,
pcap, web-targets, web-assessments, web-findings, web-security, reports, ai.

Handler audit result:
- All GET handlers reviewed for `db.add/commit`, `subprocess`, `BackgroundTasks`,
  `enqueue`, filesystem writes → **only one violation found and fixed**:
  `reports.py::download_report` performed `db.commit()` (download_count +
  audit event). Now skipped when `JUDGE_MODE` — judge.db is read-only.
- `incident_intelligence` commits are inside POST handlers (triage/correlate)
  → unreachable (method denied before routing).
- `monitoring.py` commits are inside `_process_pcap_job` background task →
  unreachable (upload POST denied; no GET triggers it).
- No WebSocket routes exist in the app.

## B. Bypass Audit — fixes applied

| Issue | Severity | Fix |
|---|---|---|
| `download_report` GET wrote to DB | HIGH | audit block gated by `JUDGE_MODE` |
| Rate-limit IP spoofable via leftmost XFF | MED | `_client_ip` now prefers `cf-connecting-ip`/`x-real-ip`, rightmost XFF fallback |
| Prefix match `/api/v1/assets` also matched `/api/v1/assetsfoo` | LOW | segment-boundary check added |
| WAL/SHM on read-only mount | MED | `build-judge-db.sh` forces `journal_mode=DELETE` + checkpoint |

Verified by tests: HEAD allowed on safe routes, OPTIONS→403, method-override
header ignored (403), encoded traversal→403/404/422, unknown prefix→403/404.

## C. Database Audit

- judge-backend mounts ONLY `storage/judge:/data:ro`; `DATABASE_URL` →
  `sqlite:////data/judge.db`. No path to `kawal_siber.db`.
- judge.db built via SQLite `.backup` (consistent snapshot), chmod 444,
  journal_mode=DELETE → no WAL side-files needed.
- Residual: app startup `init_db`/`create_all` on ro mount — tables already
  exist in snapshot so `create_all` is a no-op; must be verified at deploy.

## D. Rate Limit / Resources

- App-layer: 120 req/min/IP (in-memory; single uvicorn worker — check
  Dockerfile CMD at deploy; if multi-worker, nginx `limit_req` is the real
  edge control anyway).
- Nginx judge-proxy: `limit_req_zone` 10r/s burst 20 — effective regardless
  of backend workers.
- Compose limits: proxy 128M/0.25cpu, backend 512M/0.5cpu, frontend 512M/0.5cpu.
- EC2 headroom verified: ~14Gi free RAM, 90G disk.

## E. Tests

- `test_judge_mode.py`: **45/45 PASS** (38 original + 7 bypass cases).
- Full backend suite local run: 128 passed / 55 failed — failures are
  test-isolation/DB-state issues in unrelated suites (single-test re-run
  passes); CI remains authoritative. No judge-mode regressions.
- Frontend `tsc`/build: not run locally (no Node on this machine) —
  changes are additive (new component + env-gated banner); CI will verify.

## F. Commit hygiene

- Staged files reviewed via `git status`/`git diff` — only judge-related
  files; no `.env`, tokens, DBs, PCAPs, or runtime data.
- `tools/deep-eye` submodule pointer and `docs/aws`, `scripts/aws-academy`
  left uncommitted (unrelated work).
- Not pushed. No deploy, DNS, Cloudflare, Terraform, or AWS changes.

## Remaining risks (pre-deploy checklist)

1. Verify `init_db` no-op on read-only judge.db at first boot.
2. Verify cloudflared hostname route → `localhost:8081` (host service, not container).
3. Confirm no Cloudflare Access application covers `demo-kawal-siber.*`.
4. External no-OTP + production-still-302 tests pending deployment.
