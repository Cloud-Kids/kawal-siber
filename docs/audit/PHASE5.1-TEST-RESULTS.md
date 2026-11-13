# PHASE 5.1 — TEST RESULTS

**Date:** 2026-11-13

| Test | Result |
|---|---|
| `test_phase5_regressions.py` (7 tests: adapter authz ×4, datetime transform ×3) | 7/7 PASS |
| Full backend suite | see PHASE5.2 report (run after dep changes) |
| Frontend `tsc --noEmit` | PASS |

## New coverage added

- `_fix_naive_datetimes`: naive T/space, aware, nested, array, free-text
  safety, null/invalid passthrough.
- Adapter: authorized public IP (engine stubbed, no network), unauthorized
  IP, localhost, wrong-asset host.

## Frontend timezone parser

`parseApiTimestamp()` logic reviewed: explicit-zone regex → `new Date()`
as-is; naive → append `Z`. `formatDateTime` uses it with
`timeZone:'Asia/Jakarta'`, `id-ID`. No frontend test runner exists in repo
— logic verified by inspection + tsc; deterministic matrix documented in
REGRESSION-TEST-MATRIX.md. Browser-TZ independence is guaranteed by
explicit `timeZone` in `Intl.DateTimeFormat`.
