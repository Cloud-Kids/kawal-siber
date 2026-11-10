# KAWAL SIBER — LAPORAN EVALUASI & PENGUATAN KEAMANAN FASE 5
## PHASE 5 SECURITY HARDENING REPORT
### Kartika Cyber Hackathon 2026

---

## 1. Ringkasan Eksekutif Hardening

Sebagai bagian dari Master Engineering Prompt Fase 6 (Work Package A), telah dilaksanakan audit dan penguatan (*hardening*) mendalam terhadap subsistem **AI Triage & Unified Incident Correlation Engine** (Fase 5).

Evaluasi ini memastikan sistem tidak hanya berfungsi secara fungsional, tetapi juga kokoh secara arsitektural, terlindung dari manipulasi *prompt injection*, menerapkan pemisahan metrik yang akurat, serta memelihara integritas data SQLite tanpa regresi.

```
===========================================================================
  STATUS EVALUASI FASE 5 HARDENING: 100% TERVERIFIKASI
  - Pemisahan 3 Metrik (Severity, Correlation Strength, AI Confidence): SELESAI
  - Aturan Korelasi Spesifik Sumber (Nmap, Suricata, Deep Eye): SELESAI
  - Pelacakan Aktivitas Berulang & Idempoten: SELESAI
  - Penguatan Sanitasi Prompt Injection & Kredensial: SELESAI
  - Resolusi 2 SAWarning pada Test Suite: SELESAI (0 Warning)
  - Hasil Uji Regresi Backend: 74/74 PASS (100%)
  - Hasil Uji Worker Daemon: 18/18 PASS (100%)
===========================================================================
```

---

## 2. Pemisahan Tiga Metrik Kritis (*Metric Separation*)

Sesuai instruksi audit, sistem tidak lagi mencampuradukkan metrik teknis dengan probabilitas serangan. Tiga metrik independen kini ditegakkan pada [`unified_correlator.py`](file:///c:/Users/APIP/Documents/KAWAL%20SIBER/kawal-siber/backend/app/services/unified_correlator.py):

| Metrik | Tipe Data & Rentang | Definisi & Tujuan | Sumber Data Penentu |
| :--- | :---: | :--- | :--- |
| **A. Threat Severity** | Enum (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) | Tingkat bahaya serangan objektif berdasarkan klasifikasi teknis | Tingkat keparahan maksimum dari Suricata alert (severity 1/2), Deep Eye confirmed finding, atau insiden dasar |
| **B. Correlation Strength** | Float `0.0` – `1.0` | Derajat konvergensi teknis bukti multi-sumber (*bukan probabilitas serangan*) | Kesesuaian identitas aset (+0.20), keragaman sumber (+0.30–0.70), pencocokan port target terbuka Nmap (+0.05), status finding terkonfirmasi (+0.05) |
| **C. AI Confidence** | Float `0.0` – `1.0` | Derajat keyakinan model analisis terhadap klasifikasi taksonomi | Dihasilkan oleh engine triase (`0.85` untuk attack type teridentifikasi jelas, `0.65` untuk anomali/sumber minim) |

---

## 3. Aturan Korelasi Spesifik Sumber & Jendela Waktu Fleksibel

Sistem tidak lagi memperlakukan semua sumber dengan jendela waktu seragam ±60 menit:

1. **Suricata Network Intrusion Detection**:
   - Jendela waktu aktif: `suricata_window_minutes = 30` (serangan jaringan umumnya terjadi dalam semburan waktu sempit).
   - Validasi arah lalu lintas: Membedakan `INBOUND_TARGET` (aset diserang dari luar) dan `OUTBOUND_SOURCE` (potensi aset terkompromi).
2. **Deep Eye Web Security Assessment**:
   - Jendela waktu kerentanan: `web_window_minutes = 1440` (24 jam, karena celah aplikasi web tetap persisten hingga di-patch).
   - Bobot status temuan: Temuan `CONFIRMED` diberi bobot relasi `CONFIRMED_WEB_VULNERABILITY`, sedangkan temuan `UNVERIFIED` diberi bobot lebih rendah `UNVERIFIED_WEB_FINDING`.
3. **Nmap Discovery & Service Auditing**:
   - Diposisikan sebagai **konteks inventaris layanan historis** (`PORT_CONTEXT_FOR_ASSET`).
   - Penegasan Arsitektur: **Port terbuka BUKAN bukti serangan**, melainkan verifikasi apakah port sasaran serangan memang aktif/terekspos.

---

## 4. Pelacakan Aktivitas Berulang & Idempotensi Deduplikasi

Constraint `UNIQUE(incident_id, source_type, source_record_id)` pada tabel `incident_evidence` tetap dipertahankan untuk mencegah duplikasi baris acak. Namun, ketika event yang sama muncul berulang kali:
- Baris bukti diperbarui dengan label hitungan: `[Aktivitas Berulang: Nx]`.
- Timestamp kejadian terbaru (`evidence_timestamp`) diperbarui.
- Entri kronologi baru dicatat pada `incident_timeline_events` dengan tipe `REPEATED_OCCURRENCE`.
- Riwayat deteksi awal (`created_at`) dan kejadian pertama tetap terjaga utuh.

---

## 5. Pengerasan Terhadap Injeksi Prompt (*Prompt Injection Hardening*)

Penguatan fungsi `_sanitize()` pada [`triage_engine.py`](file:///c:/Users/APIP/Documents/KAWAL%20SIBER/kawal-siber/backend/app/services/triage_engine.py):
1. **Penyensoran Kredensial**:
   - Token Bearer & Basic Auth disensor menjadi `[REDACTED_AUTH]`.
   - Kata sandi, secret, API key, dan token disensor menjadi `[REDACTED_CRED]`.
   - Cookie dan Session ID disensor menjadi `[REDACTED_COOKIE]`.
2. **Pendeteksian & Netralisasi Pola Manipulatif**:
   - Frasa adverserial seperti `ignore previous instructions`, `system override`, `you are now a`, `developer mode`, `jailbreak`, dan `override all rules` dinetralisasi secara otomatis menjadi `[SUSPECTED_INJECTION_NEUTRALIZED]`.
3. **Flag Intervensi Manusia**:
   - Jika terdapat indikasi manipulasi prompt pada bukti mentah, hasil triase ditandai `requires_immediate_action = True`, status ditandai `REQUIRES_REVIEW`, dan catatan operator diberi peringatan audit keamanan.
4. **Pembatasan Batas String**:
   - Setiap bidang teks bukti dibatasi maksimal 300 karakter untuk mencegah teknik *denial-of-context* atau *token stuffing*.

---

## 6. Resolusi Test Warnings & Integritas SQLite Concurrency

### A. Resolusi Dua `SAWarning` pada Pytest
- **Gejala Awal**: Muncul 2 peringatan `SAWarning: transaction already deassociated from connection` saat eksekusi `test_database_integrity.py`.
- **Akar Masalah**: Fixture `db_session` pada `tests/conftest.py` memanggil `transaction.rollback()` secara buta pada blok `finally`, padahal ketika terjadi pelanggaran constraint foreign key atau check constraint di SQLite, transaksi sudah di-rollback oleh koneksi database.
- **Perbaikan Rekayasa**:
  ```python
  if transaction.is_active:
      transaction.rollback()
  ```
- **Hasil**: Peringatan berkurang dari 2 menjadi **0 (nol)**.

### B. Resolusi Pytest-Asyncio Deprecation Warning
- Ditambahkan file konfigurasi `backend/pytest.ini`:
  ```ini
  [pytest]
  asyncio_mode = strict
  asyncio_default_fixture_loop_scope = function
  ```
- **Hasil**: Seluruh 74 backend tests berjalan bersih tanpa peringatan apapun.

---

## 7. Status Konsistensi Pengujian Fase 5

Dokumentasi diselaraskan dengan hasil pengujian aktual:
- **Total Kriteria Uji**: 15
- **Hasil**: **14 PASS, 0 FAIL, 1 SKIPPED**
- **Keterangan Status SKIPPED**:
  - `OLLAMA_01`: Service Ollama offline pada port `11434`. Sesuai aturan hackathon, pengujian ini ditandai **SKIPPED** (tidak dipalsukan menjadi PASS).
  - Terbukti bahwa sistem secara sempurna beralih (*graceful fallback*) ke `RuleBasedProvider` tanpa gangguan operasional.

