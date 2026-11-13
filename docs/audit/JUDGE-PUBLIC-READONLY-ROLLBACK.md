# JUDGE PUBLIC READ-ONLY — Rollback Plan

Rollback is **additive-only**: nothing in production was modified, so removing
the judge stack restores the prior state completely.

## Level 1 — Disable public access (fastest, keeps stack for debugging)

On EC2 host:

```bash
# Option A: stop the tunnel route by removing the public hostname in
# Cloudflare Zero Trust → Tunnels → kawal-siber → Public Hostnames
# (delete ONLY the demo-kawal-siber.smkcloud.web.id route)

# Option B: stop the judge proxy so nothing listens on 8081
cd /opt/kawal-siber/app   # or wherever judge compose lives
docker compose -f deploy/judge-demo/compose.judge.yaml -p kawal-judge stop judge-proxy
```

Effect: hostname stops resolving to any service; production unaffected.

## Level 2 — Remove judge stack entirely

```bash
docker compose -f deploy/judge-demo/compose.judge.yaml -p kawal-judge down -v
rm -rf storage/judge/        # sanitized dataset only — safe to delete
```

## Level 3 — Revert code (if needed)

Judge code is additive and env-gated:

```bash
git revert <judge-commit>    # or checkout files individually
```

Files: `backend/app/judge_mode.py`, `backend/tests/test_judge_mode.py`,
`deploy/judge-demo/*`, `frontend/components/judge/*`, `scripts/build-judge-db.sh`,
plus small edits to `backend/app/main.py`, `frontend/Dockerfile`,
`frontend/app/layout.tsx`.

## What is NEVER touched by rollback

- Production containers, `kawal_siber.db`, volumes, ports
- Cloudflare Access application for `kawal-siber.smkcloud.web.id`
- Tunnel connector config (only the added public hostname route is removed)
- Security Groups, IAM, Terraform state

## Verification after rollback

```bash
curl -sI https://kawal-siber.smkcloud.web.id/   # expect 302 Access challenge
curl -s  http://localhost/api/v1/monitoring/statistics | head -c 100  # prod API alive
```
