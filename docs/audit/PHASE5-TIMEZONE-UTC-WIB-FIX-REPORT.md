# PHASE 5 — TIMEZONE UTC→WIB FIX REPORT

**Date:** 2026-11-13

## Root cause (confirmed)

SQLite `CURRENT_TIMESTAMP` stores UTC naive (`YYYY-MM-DD HH:MM:SS`, no
zone). API serialized it without `Z`/offset → `new Date()` in browser
parsed as **local time** → Asia/Jakarta formatter displayed UTC wall-clock
as if WIB (~7h behind real time).

## Implementation

| File | Change |
|---|---|
| `backend/app/main.py` | `utc_timestamp_guard` middleware: for `application/json` responses, appends `Z` to naive ISO-8601 datetimes (`_NAIVE_DT_RE`). Aware timestamps (`+00:00`, `Z`) untouched. |
| `frontend/lib/utils.ts` | new `parseApiTimestamp()`: explicit-zone strings parse as-is; naive strings treated as UTC (`+ 'Z'`). `formatDateTime()` uses it; still formats with `timeZone: 'Asia/Jakarta'`, `id-ID`. |

## Design decisions

- **No DB migration** — historical naive-UTC rows untouched; serialization
  fix makes them display correctly.
- **No +7h anywhere** — backend emits UTC, frontend converts.
- Naive→UTC assumption is safe: all `server_default=func.now()` and
  `datetime.now(timezone.utc)` writes are UTC-sourced.
- Components using `new Date(apiTs).toLocaleString()` directly also heal
  automatically once API emits `Z`.

## Known limitation

Regex appends `Z` to any JSON string that is *exactly* a naive datetime —
free-text fields ending in a timestamp-like string could get a cosmetic
`Z`. Rare; documented, not blocking.

## Tests

- Regex unit test: naive `T` and space formats → `Z`; `+00:00` untouched.
- Full backend suite: 188 passed.
- Frontend `tsc --noEmit`: PASS.
