# KAWAL SIBER — AUDIT PRA-IMPLEMENTASI FASE 6
## EVALUASI KEAMANAN FASE 5 & KESIAPAN AUTOMATED REPORTING
### Kartika Cyber Hackathon 2026

---

## 1. Ringkasan Eksekutif Audit

Audit menyeluruh terhadap seluruh basis kode, basis data, dan modul KAWAL SIBER (Fase 1 hingga Fase 5) telah dilaksanakan pada lingkungan lokal Windows tanpa Docker.

Status integritas sistem saat audit:
- **Basis Data SQLite**: WAL mode aktif (`PRAGMA journal_mode=WAL`), foreign keys aktif, revisi migrasi Alembic berada pada `0005` (Fase 5).
- **Backend Tests**: 74 pengujian unit/integrasi telah dijalankan dan **74/74 PASS (100%)**.
- **Worker Tests**: 18 pengujian worker lulus **18/18 PASS (100%)**.
- **Master Acceptance Test Fase 5**: 14 PASS, 0 FAIL, 1 SKIP (Ollama offline).
- **Frontend Next.js 15**: 19 rute App Router terkompilasi bersih tanpa kesalahan TypeScript (`npm run type-check`: 0 error).

---

## 2. Inventaris Modul & Komponen Eksisting

| Komponen | Status Implementasi | Lokasi Kode Sumber | Kondisi & Catatan Audit |
| :--- | :---: | :--- | :--- |
| **Manajemen Aset & Scope** | Lengkap | `backend/app/api/routes/assets.py`, `scopes.py` | Berjalan stabil, validasi CIDR dan otorisasi ketat |
| **Nmap Scanner Worker** | Lengkap | `worker/nmap_scanner.py`, `xml_parser.py` | Profil scanning terkunci, deteksi nmap.exe lokal |
| **Suricata IDS & PCAP** | Lengkap | `backend/app/services/suricata_engine.py`, `eve_processor.py` | Ingesti EVE JSON, analisis PCAP offline aman |
| **Deep Eye Web Security** | Lengkap | `backend/app/integrations/deep_eye/` | Profil PASSIVE & SAFE_LOCAL, sanitasi bukti |
| **AI Provider Abstraction** | Lengkap | `backend/app/services/ai_provider.py` | `RuleBasedProvider` aktif, `OllamaProvider` offline (graceful) |
| **AI Triage Engine** | Perlu Hardening | `backend/app/services/triage_engine.py` | Sanitasi input dasar ada; perlu penguatan prompt injection |
| **Unified Correlator** | Perlu Hardening | `backend/app/services/unified_correlator.py` | Korelasi berbasis IP/aset; perlu pemisahan 3 metrik |
| **Incident Management** | Lengkap | `backend/app/api/routes/incidents.py`, `incident_intelligence.py` | Siklus hidup 6 status, kontrol persetujuan operator |

---

## 3. Temuan Audit Khusus Work Package A (Phase 5 Hardening)

### Temuan A.1: Pemisahan Tiga Metrik Kritis
*Kondisi Eksisting*:
Pada `unified_correlator.py`, fungsi `_calculate_confidence()` menghasilkan satu nilai `confidence_score` yang saat ini mencerminkan keberadaan variasi sumber data (Suricata, Deep Eye, Nmap).
*Rekomendasi Rekayasa*:
Wajib memisahkan secara eksplisit tiga metrik berbeda:
1. **Threat Severity**: Tingkat bahaya serangan objektif berdasarkan signature / CVE temuan (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
2. **Correlation Strength**: Seberapa kuat hubungan teknis antar bukti (kecocokan port spesifik, arah paket, protokol, dan endpoint terdampak). Rentang: 0.0 – 1.0 (bukan probabilitas serangan).
3. **AI Confidence**: Tingkat keyakinan model analisis terhadap hasil klasifikasinya (0.0 – 1.0).

### Temuan A.2: Aturan Korelasi Spesifik Sumber (*Source-Specific Rules*)
*Kondisi Eksisting*:
Korelasi masih menggunakan jendela waktu seragam (±60 menit) untuk seluruh sumber data, dan memperlakukan temuan web yang belum terverifikasi (`UNVERIFIED`) sebanding dengan alert IDS.
*Rekomendasi Rekayasa*:
1. **Nmap**: Harus diposisikan murni sebagai *service & port inventory context* historis (port terbuka bukan bukti serangan aktif).
2. **Suricata**: Mengharuskan validasi arah traffic (`is_target` vs `is_source`) dengan jendela waktu deteksi aktif yang lebih ketat (misal 15–30 menit).
3. **Deep Eye**: Memverifikasi kecocokan port/URL spesifik; temuan berstatus `UNVERIFIED` diberi bobot lebih rendah dibanding `CONFIRMED`.

### Temuan A.3: Pelacakan Aktivitas Berulang (*Repeated Occurrence Tracking*)
*Kondisi Eksisting*:
Deduplikasi bukti saat ini menggunakan constraint `UNIQUE(incident_id, source_type, source_record_id)` yang menolak duplikasi baru secara langsung.
*Rekomendasi Rekayasa*:
Sistem tidak boleh menghilangkan konteks kejadian berulang. Jika event yang sama berulang:
- Tambahkan hitungan kejadian (*occurrence_count*).
- Perbarui timestamp kejadian terakhir (*last_seen*).
- Tambahkan entri kronologi pada `incident_timeline_events`.

### Temuan A.4: Pengerasan Prompt Injection
*Kondisi Eksisting*:
Fungsi `_sanitize()` telah menghapus karakter kontrol, namun payload adverserial yang mengandung instruksi teks berbahasa inggris ("IGNORE PREVIOUS INSTRUCTIONS") perlu diuji ketahanannya.
*Rekomendasi Rekayasa*:
- Isolasi ketat data bukti ke dalam format JSON terstruktur yang ditandai `untrusted_data`.
- Batasi panjang setiap teks masukan maksimal 300–500 karakter.
- Redaksi kata kunci sensitif (password, authorization bearer, API key).
- Tandai hasil sebagai `REQUIRES_REVIEW` jika mendeteksi instruksi manipulatif.

### Temuan A.5: Resolusi Peringatan Pengujian (*Test Warnings*)
*Kondisi Eksisting*:
Terdapat 2 peringatan `SAWarning: transaction already deassociated from connection` pada `tests/test_database_integrity.py`.
*Hasil Remediasi Audit*:
Penyebab teridentifikasi: fixture `db_session` di `tests/conftest.py` memanggil `transaction.rollback()` tanpa mengecek apakah transaksi masih aktif setelah error constraint SQLite.
Remediasi diterapkan:
```python
if transaction.is_active:
    transaction.rollback()
```
Hasil: Peringatan **0 (nol)**, 74 pengujian unit berjalan bersih.

---

## 4. Evaluasi Kesiapan Work Package B (Reporting Engine)

### Analisis Kebutuhan Pelaporan:
1. **Dependensi Library PDF**:
   - `reportlab` diperlukan untuk membuat PDF profesional berstandar korporat/militer pada Windows.
   - Perlu memeriksa ketersediaan `reportlab` di virtual environment backend.
2. **Skema Basis Data Baru**:
   - Diperlukan tabel `generated_reports` melalui Alembic migration `0006`.
3. **Struktur Modular `backend/app/reporting/`**:
   - Engine terpusat dengan 5 tipe laporan (Executive, Technical, Assessment, Operations, AI Intelligence) dan 4 format ekspor (PDF, HTML, JSON, CSV).
4. **Proteksi Formula Injection**:
   - Ekspor CSV wajib menyensor karakter prefix berbahaya (`=`, `+`, `-`, `@`, `\t`, `\r`).
5. **Worker Daemon**:
   - Pembuatan laporan dijalankan asinkron oleh Python worker yang sudah ada (`worker/main.py`), tanpa membuat daemon kedua.

---

## 5. Rencana Tindakan Terstruktur

1. **Langkah 1 (Hardening Phase 5)**:
   - Perbarui `unified_correlator.py` dengan pemisahan 3 metrik (Severity, Correlation Strength, AI Confidence), korelasi spesifik sumber, jendela waktu fleksibel, dan pelacakan *occurrence count*.
   - Perkuat `triage_engine.py` dengan redaksi kredensial dan deteksi *prompt injection*.
   - Simpan `docs/reports/PHASE-5-HARDENING-REPORT.md`.

2. **Langkah 2 (Alembic Migration 0006 & Database Extension)**:
   - Buat tabel `generated_reports` dengan kolom checksum SHA-256, ukuran file, status, dan metadata.

3. **Langkah 3 (Reporting Engine Architecture)**:
   - Bangun modul `backend/app/reporting/` lengkap dengan 5 generator laporan dan 4 eksportir (PDF, HTML, JSON, CSV).

4. **Langkah 4 (Worker Extension & API Routes)**:
   - Tambahkan job handler `claim_next_pending_report()` di worker.
   - Daftarkan endpoint `/api/v1/reports/*` di backend FastAPI.

5. **Langkah 5 (Frontend Integration)**:
   - Bangun halaman `/reports`, `/reports/create`, `/reports/[id]`, dan `/analytics` di Next.js App Router.

6. **Langkah 6 (Verifikasi & Pengujian Master Acceptance)**:
   - Buat dan jalankan `phase6_acceptance_test.py`.
   - Dokumentasikan laporan akhir di `docs/reports/PHASE-6-REPORT.md`.

