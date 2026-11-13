# PHASE 5 — REGRESSION TEST REPORT

**Date:** 2026-11-13

## Results (actual, local WSL Ubuntu 24.04)

| Suite | Result |
|---|---|
| Backend full suite (`pytest tests/`) | **188 passed, 1 skipped, 0 failed** (was 183+5 new) |
| New `test_phase5_regressions.py` | 5/5 PASS |
| Judge mode tests | included in suite — PASS |
| Frontend `tsc --noEmit` | PASS (exit 0) |
| Frontend `next build` (judge flag) | PASS — see note |

## Issues found & fixed during Phase 5

1. **Regex double-quote bug** — lookahead `(?=")` + replacement `\1Z"`
   produced `"…Z""`; fixed to `\1Z`. Caught by new test.
2. **Middleware body-consumption bug** — returning the original response
   after draining `body_iterator` yielded empty bodies → 19 test failures
   (`JSONDecodeError`). Fixed by always rebuilding the JSON response.
   Caught by full suite, not by unit tests — validates running regression.

## Fixed-timestamp matrix (contract)

| API value | Displays (WIB) |
|---|---|
| `2026-11-13T09:00:00Z` | 13 Nov 2026, 16:00 |
| `2026-11-13T09:00:00+00:00` | 16:00 |
| `2026-11-13 09:00:00` (naive, SQLite UTC) | 16:00 (via `Z` suffix / parser) |
| `2026-11-13T11:00:00+02:00` | 16:00 (instant-based) |

## Not tested (requires deployment)

- Real assessment #18+ against `34.209.65.97` end-to-end (needs EC2 +
  authorized target; local tests stub network engine).
- Live browser verification of WIB across all pages.
