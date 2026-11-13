# PHASE 5.4G — DEPENDABOT RESCAN REPORT

GitHub Dependabot alerts API returned 403 for the fine-grained PAT
(missing Dependabot alerts permission). Rescan status: PENDING / NOT VERIFIED.

Local verification (Phase 5.3) stands: 11/12 fixed locally, minimatch
unresolved (dev-only). GitHub-side alert states require either PAT
permission update or manual dashboard check post-merge to main.

| Alert | Dependency | Local status | GitHub status |
|---|---|---|---|
| #11/#10 | anyio | fixed (4.12.1) | PENDING rescan |
| #3 | pytest | fixed (8.4.2) | PENDING rescan |
| #51/#50/#37 | sharp | fixed (0.35.5) | PENDING rescan |
| #45/#46/#47/#24 | postcss | fixed (8.5.32 override) | PENDING rescan |
| #12 | plugin-kit | fixed (0.4.1) | PENDING rescan |
| #56 | minimatch | UNRESOLVED (dev-only) | expected open |
