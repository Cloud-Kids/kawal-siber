# PHASE 5 — CHANGELOG & FILE IMPACT

## Files changed

| File | Root cause | Risk |
|---|---|---|
| `backend/app/integrations/deep_eye/adapter.py` | Deep Eye P0 — accept `extra_allowed_hosts`, forward to validator | LOW — new optional param, default None = old behavior |
| `backend/app/services/web_assessment_service.py` | Deep Eye P0 — pass linked asset's `target_ip` at execution | LOW — additive; only fires when asset linked |
| `backend/app/main.py` | Timezone P1 — `utc_timestamp_guard` middleware + `_NAIVE_DT_RE` | MED — touches every JSON response; mitigated by full suite |
| `frontend/lib/utils.ts` | Timezone P1 — `parseApiTimestamp()` + `formatDateTime` uses it | LOW — display-only |
| `backend/tests/test_phase5_regressions.py` | NEW — 5 regression tests | none |
| `docs/audit/PHASE5-*.md` | NEW — 5 reports | none |

## Explicitly NOT changed

- No DB migration, no model changes, no Alembic.
- No authz policy broadening — `DEFAULT_ALLOWED_HOSTS` untouched.
- No judge-mode files touched (4 commits `c2e7ee2..b6c3b2f` intact).
- No validator logic changes.
- No frontend component rewrites — backend `Z` suffix heals direct
  `new Date()` usages automatically.

## Commits

Pending — will be split: `fix(deep-eye)` / `fix(timezone)` / `test`.
