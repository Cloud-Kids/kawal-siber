# PHASE 5.2 — DEPENDABOT VERIFICATION MATRIX

**Date:** 2026-11-13 · Local versions only — GitHub rescan pending push.

| Alert | Package | Old | New | Advisory fixed locally? | Evidence |
|---|---|---|---|---|---|
| #11 Critical | anyio | 4.12.1 | 4.12.1 | YES (pre-existing) | requirements.txt pin |
| #10 Moderate | anyio | 4.12.1 | 4.12.1 | YES | same |
| #3 Moderate | pytest | 8.4.2 | 8.4.2 | YES | same |
| #51/#50/#37 High | sharp family | 0.34.5 | 0.35.5 | YES | `npm ls sharp` = 0.35.5 |
| #45/#46/#47/#24 PostCSS | postcss | 8.4.31 nested | 8.5.32 all | YES | `npm ls postcss` all deduped/overridden |
| #56 Moderate | minimatch | 10.2.6 | 10.2.6 | **NO — no patched release compatible** | typescript-eslint requires ^10 |
| #12 Low | @eslint/plugin-kit | 0.2.8 | 0.4.1 | YES | eslint 9.39.5 dep tree |

## Counts

- **FIXED LOCALLY — AWAITING GITHUB RESCAN:** 11 of 12
- **NOT FIXABLE (upstream pending, dev-only):** 1 (minimatch via
  @typescript-eslint chain — covers alerts #56 and the typescript-eslint
  moderates shown by npm audit)

Note: user's snapshot listed 12 alerts; npm audit currently reports the
typescript-eslint/minimatch cluster as 6 moderate entries — same root
advisory, counted once here.
