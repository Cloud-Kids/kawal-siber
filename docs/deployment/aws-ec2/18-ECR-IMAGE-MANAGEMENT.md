# 18. Amazon ECR Image Management & Tagging Policy

## 1. ECR Repositories Architecture

Four dedicated private repositories in Amazon ECR:
1. `kawal-siber-frontend`
2. `kawal-siber-backend`
3. `kawal-siber-worker`
4. `kawal-siber-tools-agent`

---

## 2. Tagging Policy & Immutability

### 2.1 Immutable Release Tags
All ECR repositories enforce **`imageTagMutability: IMMUTABLE`**. Once an image is pushed with a release tag, it cannot be overwritten or altered. This guarantees absolute auditability and tamper protection.

### 2.2 Tag Naming Convention
1. **Primary Release Tag**: `sha-<short_commit_sha>` (e.g. `sha-4a2b91c0`).
2. **Semantic Release Tag** (on release tags): `v6.1.0`.
3. **Mutable Convenience Tag**: `latest` is only used for local developer pulls; production task definitions reference exact image digests (`@sha256:...`) or immutable commit SHA tags.

---

## 3. Vulnerability Scanning & Security Gates

- **Scan on Push**: Every image pushed to ECR is automatically analyzed using AWS native Basic / Enhanced scanning (Amazon Inspector).
- **Severity Thresholds**: Images containing unpatched `CRITICAL` Common Vulnerabilities and Exposures (CVEs) fail deployment verification.

---

## 4. Lifecycle Policies

To maintain storage hygiene and cost efficiency without compromising rollback capabilities:
- **Tagged Release Images**: Retain the last 30 tagged release images.
- **Untagged / Expired Images**: Purged automatically after 7 days.

