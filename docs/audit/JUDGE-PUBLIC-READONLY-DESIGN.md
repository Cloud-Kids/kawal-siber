# KAWAL SIBER — Public Judge Read-Only Demo: Architecture Proposal (Phase 2)

**Date:** 2026-11-13
**Status:** 📐 PROPOSAL — menunggu approval sebelum implementasi/deploy.

---

## 1. Hasil Recon (Phase 1)

| Komponen | Temuan |
|---|---|
| Compose | 4 service: `proxy`(nginx, satu-satunya port publik), `frontend`(Next.js :3000), `backend`(FastAPI :8000), `worker` |
| Nginx | `server_name _` — **satu server block untuk semua hostname**; route `/api/v1/` → backend, `/` → frontend |
| API | ~54 endpoint GET/POST/PATCH/DELETE di 9 route files |
| DB | SQLite tunggal `storage/kawal_siber.db` di bind mount — **shared prod+judge risk** |
| Cloudflare | 1 tunnel `23048f89`, 1 hostname `kawal-siber.*` → `localhost:80`; Access app hanya di hostname itu |
| EC2 | `i-0064201c97bc68195` r6i.large (app) + `i-0ceb74a85a3b08ce3` t2.nano (**idle, bisa dipakai**) |
| t2.nano | SSH OK, kosong — kandidat host judge environment |

## 2. Opsi Arsitektur

### Opsi A — Judge stack di EC2 utama (RECOMMENDED)
Tambah 2 container di compose yang sama, network internal:

```
demo-kawal-siber.smkcloud.web.id
  → cloudflared (sama, tambah public hostname → localhost:8081)
  → judge-proxy (nginx :8081, server_name demo-*)
      ├─ /api/v1/* → judge-backend:8001  (JUDGE_MODE=true, DB terpisah)
      └─ /         → judge-frontend:3001 (build sama, NEXT_PUBLIC_JUDGE_MODE=1)
```

**Plus:** judge-backend pakai **copy SQLite terpisah** `judge.db` hasil dump tersanitasi — bukan file prod.

- ✅ Satu cloudflared, satu tunnel — tambah hostname saja
- ✅ Prod stack tidak tersentuh (container terpisah, port internal)
- ✅ DB benar-benar terpisah (file berbeda, mount berbeda)
- ⚠️ Butuh image build tambahan (~resource, tapi r6i.large cukup)
- ⚠️ Frontend butuh mode flag untuk hide tombol operasional

### Opsi B — Judge stack di t2.nano (paling terisolasi)
Deploy compose judge-only di t2.nano + cloudflared kedua (token sama, hostname tambahan di dashboard CF).

- ✅ Isolasi maksimal — instance fisik berbeda
- ✅ Prod sama sekali tidak tersentuh
- ❌ Butuh clone repo + build image di t2.nano (1GB RAM — build lambat/berisiko)
- ❌ Tambah biaya instance running
- ❌ Perlu setup cloudflared + DNS route baru

### Opsi C — Static snapshot (paling aman, paling terbatas)
Export data → generate static HTML/JSON site, host di mana saja.

- ✅ Zero backend risk
- ❌ Tidak interaktif — juri tidak bisa "coba" API; nilai demo turun

## 3. Rekomendasi: Opsi A

Alasan: isolasi cukup (proses+DB+port terpisah), reuse image & tooling, nol perubahan prod, t2.nano tetap idle/stop untuk hemat kredit.

## 4. Desain Keamanan Inti

### 4.1 judge-backend (`JUDGE_MODE=true`)
Middleware baru `app/middleware/judge_mode.py`:
- Allowlist eksplisit route GET yang boleh: `/api/v1/health`, `/assets*`, `/scan-scopes*`, `/scans*` (GET only), `/security-events*`, `/security-alerts*`, `/monitoring/statistics`, `/pcap*` (GET), `/web-targets*` GET, `/web-assessments*` GET, `/web-findings*`, `/incidents*` GET, `/incident-intelligence*`, `/reports*` GET + download UUID tervalidasi, `/ai/health`
- **Semua method non-GET → 403** tanpa kecuali
- **Semua route di luar allowlist → 404/403** (deny by default)
- `/docs`, `/openapi.json` → disabled di judge mode
- Response strip: tidak ada stack trace, path internal, atau env
- Rate limit sederhana (mis. 60 req/min per IP) via middleware counter
- DB: `DATABASE_URL=sqlite:////data/judge.db` — file hasil `sqlite3 .dump` + sanitasi, **read-only mount** (`:ro`)

### 4.2 Sanitasi data judge.db
Dump dari prod lalu strip: tidak ada credentials (memang tidak ada), ganti `generated_by` → `judge-demo`, pastikan tidak ada field internal paths/hostname. Label: records nyata tetap nyata; tidak ada data palsu.

### 4.3 judge-frontend
Build image sama dengan env `NEXT_PUBLIC_JUDGE_MODE=1` → komponen hide tombol POST (Tambah Target, Mulai Scan, Upload PCAP, dll). Backend 403 tetap pertahanan utama — UI hiding hanya UX.
Banner persistent: "PUBLIC JUDGE DEMO — READ ONLY".

### 4.4 Nginx judge-proxy
`server_name demo-kawal-siber.smkcloud.web.id;` → upstream judge services. Port 8081 internal only — cloudflared `localhost:8081`.

### 4.5 Cloudflare
Tambah **Public Hostname** `demo-kawal-siber` di tunnel existing → `http://localhost:8081`. **Tanpa Access app** → publik. WAF/rate-limit rule opsional via dashboard (butuh approval/token).

## 5. API Permission Matrix (ringkas)

| Route group | Methods allowed di judge mode |
|---|---|
| health | GET |
| assets, scopes, web-targets | GET only |
| scans, scan results | GET only |
| monitoring statistics/events/alerts | GET only |
| pcap analyses | GET only |
| web-assessments, findings | GET only |
| incidents, evidence, timeline, intelligence | GET only |
| reports list/detail/audit-chain | GET only |
| report download | GET + UUID validation + path containment |
| **semua POST/PUT/PATCH/DELETE** | **403 always** |
| /docs, /openapi.json | disabled |

## 6. Resource assessment (r6i.large)

- +2 container kecil (backend FastAPI idle ~100MB, frontend Next ~150MB, nginx ~20MB) → RAM masih aman (16GB total, prod pakai ~2-3GB)
- Build image: reuse base images, cache Docker layers → +5-10 menit build pertama
- Storage: judge.db copy ~beberapa MB

## 7. Risiko & mitigasi

| Risiko | Mitigasi |
|---|---|
| Bug di allowlist → endpoint write lolos | Deny-by-default + test negatif wajib (POST semua route → 403) |
| judge.db berisi data sensitif | Sanitasi script + review dump sebelum deploy |
| Frontend tombol masih terlihat | Backend 403 = enforcement; UI flag = polish |
| Resource exhaustion oleh publik | Rate limit middleware + Cloudflare WAF (opsional) |
| Prod terganggu | Container/port/network terpisah; rollback = remove 2 service + hostname |

## 8. Rencana implementasi (setelah approval)

1. `backend/app/middleware/judge_mode.py` + env flag + route allowlist
2. `deploy/judge-demo/compose.judge.yaml` + `judge-nginx.conf` + Dockerfile judge-frontend (env flag)
3. Script `scripts/build-judge-db.sh` — dump+sanitize prod DB → `storage/judge/judge.db`
4. Frontend: `NEXT_PUBLIC_JUDGE_MODE` conditional rendering (hide action buttons, banner)
5. Tests: `backend/tests/test_judge_mode.py` — semua POST → 403, allowlist GET → 200, docs disabled
6. Deploy: compose up judge services → tambah tunnel hostname → test eksternal
7. Report `JUDGE-PUBLIC-READONLY-IMPLEMENTATION-REPORT.md`

## 9. Yang TIDAK akan dilakukan

- Tidak menyentuh Access app / hostname prod
- Tidak membuka port baru di SG (tetap tunnel-only)
- Tidak mengubah prod DB/schema
- Tidak pakai t2.nano (hemat kredit, cukup resource di instance utama)

**Menunggu approval untuk Phase 3.** Konfirmasi: setuju Opsi A? Ada preferensi tambahan (mis. hostname `demo-kawal-siber` vs lain)?
