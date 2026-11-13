# PHASE 5.2 — DEPENDENCY SECURITY INVENTORY & REMEDIATION

**Date:** 2026-11-13

## Baseline → Final

| Package | Before | After | Advisory | Status |
|---|---|---|---|---|
| anyio (py) | 4.12.1 | 4.12.1 | TLSStream IDNA / process-pool | already patched (PR#4) |
| pytest (py) | 8.4.2 | 8.4.2 | tmpdir | already patched |
| postcss | 8.5.32 direct / **8.4.31 nested in next** | **8.5.32 everywhere** (override) | GHSA-qx2v, -6g55, -fxqj, -r28c, XSS | FIXED LOCALLY |
| sharp | 0.34.5 | **0.35.5** | libvips/libheif/librsvg CVEs | FIXED LOCALLY |
| @eslint/plugin-kit | 0.2.8 | **0.4.1** (via eslint 9.39.5) | ReDoS GHSA-xffm | FIXED LOCALLY |
| eslint | 9.15.0 | **9.39.5** | (enabler for plugin-kit) | upgraded, peer-compatible |
| minimatch (via @typescript-eslint) | 10.2.6 | 10.2.6 | GHSA-g3hv DoS | **NOT FIXABLE** — see below |
| @typescript-eslint/* | 8.72.1 | 8.72.1 | depends on vulnerable minimatch | dev-only, upstream pending |

## Changes made

- `frontend/package.json`: `eslint` 9.15.0→9.39.5; added
  `"overrides": {"postcss": "8.5.32"}` (forces next's nested postcss too).
- `npm audit fix` applied safe bumps (sharp→0.35.5 via lockfile).
- `frontend/package-lock.json` regenerated.

## Unfixable residual (documented, not hidden)

`minimatch` GHSA-g3hv-75wg-m249 affects 7.0.0–11.0.0; patched line is
≥11.0.1 but `@typescript-eslint/*@8.72.2` (latest) still requires
`minimatch@^10.2.2`. No compatible patched release exists yet.
- **Dev-only** (lint/build toolchain, not shipped to runtime).
- DoS requires attacker-controlled glob patterns in lint config — not
  reachable in this project's usage.
- Re-check after typescript-eslint releases a minimatch-11-compatible
  version. `npm audit fix` confirms no automatic fix available.

## Python side

`pip check` clean; anyio 4.12.1 / pytest 8.4.2 already patched — no changes
needed this phase.
