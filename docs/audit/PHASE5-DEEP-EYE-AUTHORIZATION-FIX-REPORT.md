# PHASE 5 — DEEP EYE AUTHORIZATION FIX REPORT

**Date:** 2026-11-13 · **Branch:** `feat/judge-public-readonly`

## Root cause (confirmed in Phase 4 investigation)

`create_web_target()` authorized external IPs via linked Asset
(`extra_hosts.add(asset.target_ip)`), but `execute_assessment_job()` never
forwarded that context to `deep_eye_adapter.execute_assessment()` →
validator rejected public IPs → FAILED before engine ran.

## Implementation

| File | Change |
|---|---|
| `backend/app/integrations/deep_eye/adapter.py` | `execute_assessment()` accepts `extra_allowed_hosts: Optional[set]`, forwarded to `parse_and_validate_target_url` |
| `backend/app/services/web_assessment_service.py` | `execute_assessment_job()` re-derives authz at execution time: `extra_hosts = {target.asset.target_ip}` only when `target.asset_id` + asset + `target_ip` present; passes `extra_allowed_hosts=extra_hosts or None` |

## Security properties preserved

- Hosts come **only** from the asset actually linked to the target —
  never from request input, never wildcard, never global.
- Authorization re-validated at execution (asset must still exist).
- `DEFAULT_ALLOWED_HOSTS` unchanged; validator logic untouched.
- Public IP **without** asset link → still rejected (test-verified).
- Different asset's IP → still rejected (test-verified).
- Judge mode unaffected: assessment endpoints remain POST→403.

## Tests (`test_phase5_regressions.py`)

- authorized public IP + stubbed engine → `success=True` (no external calls)
- unauthorized public IP → `success=False`, scope error
- localhost → allowed
- wrong asset host → rejected
- naive/aware datetime regex → `Z` appended correctly, aware untouched

## Before / after

- Before: `http://34.209.65.97:80/` → FAILED, "outside authorized scope", duration 0
- After: same target with linked asset → passes validation, engine pipeline runs
