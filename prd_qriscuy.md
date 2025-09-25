
# PRD — qriscuy (Python 3.11)

> **Catatan:** Setiap perubahan fitur, scope, atau perilaku aplikasi **WAJIB** diupdate di file ini. Semua perubahan harus tetap mematuhi `project_rules.md`.

**Versi**: 0.1 (Draft)  
**Owner**: dre  
**Tujuan**: Generator QRIS dengan *fingerprint in-QR* untuk konfirmasi pembayaran mandiri (tanpa integrasi bank/aggregator). Dana selalu mendarat langsung ke QRIS milik user; sistem hanya menambahkan metadata (fingerprint/signature) ke payload QR + alur konfirmasi via scan-callback.

---

## 1) Ringkasan
- **Masalah**: Ingin konfirmasi pembayaran otomatis saat customer scan & bayar QRIS milik user **tanpa** menahan dana dan **tanpa** integrasi ke bank/aggregator.
- **Solusi**:
  1) Sisipkan **fingerprint (FP)** + **signature (HMAC)** ke **Tag 62** (Additional Data) pada payload EMV/QRIS (merchant ID asli user tetap).  
  2) Saat QR discan, **scan-client** (POS/app/web) mengirim **FP** ke endpoint `qriscuy` → status invoice berubah **PENDING/SCANNED**.  
  3) Karena tidak ada akses mutasi bank, **kebijakan sukses** bisa:
     - **Mode Fast**: tandai **SUCCESS** setelah FP tervalidasi (risiko false-positive dijelaskan).
     - **Mode Safe**: tetap **PENDING** sampai ada **konfirmasi manual** (dashboard) atau **bukti bayar** (unggah—opsional).  
  4) Tidak ada escrow. Dana langsung masuk ke QRIS user karena field merchant tidak diubah.

> **Catatan penting**: Tanpa data mutasi/settlement, FP **bukan bukti final pembayaran**. PRD ini menyediakan dua mode (Fast/Safe) agar bisa dipilih sesuai kebutuhan risiko.

---

## 2) Scope & Non‑Scope
**Scope**
- Generate QRIS **statis/dinamis** dari payload QRIS user (merchant tetap milik user).  
- Sisipkan **Tag 62** berisi `FP`, `SIG`, `TS` (timestamp), `ALG` (opsional).  
- **QR renderer** dengan tema/desain *brand* `qriscuy` (logo, label, margin/quiet zone, error correction).  
- **REST API** untuk: generate QR, terima callback scan (`/scan`), lihat status invoice, dan webhook ke sistem merchant (opsional).  
- **Keamanan**: HMAC, API key statis (v0.1), rate limit.  
- **Observability**: logging JSON terstruktur, middleware request logging, ekspor metrik Prometheus via `/metrics`.  
- **Distribusi**: script `run.sh` + image Docker resmi (Python 3.11 slim) siap deploy.

**Non‑Scope**
- **Integrasi bank/aggregator** (mutasi/settlement API).  
- **Escrow** atau penahanan dana.  
- **Chargeback/dispute** otomatis.  
- **Dekoding QRIS resmi full** di luar kebutuhan Tag 62 (kita tidak memodifikasi merchant account fields).  

---

## 3) Asumsi & Batasan
- Wallet/e-wallet **mengabaikan** tag tambahan yang tidak dikenal (praktik umum EMV).  
- Menyisipkan data ke **Tag 62** tidak memblokir pembayaran & tidak mengubah routing dana.  
- Scan-client dapat dikontrol (POS/web/app yang kita sediakan) sehingga **selalu** mengirim FP ke API `qriscuy`. Jika customer menggunakan scanner pihak ketiga yang tidak memanggil `/scan`, maka sistem tidak mendapatkan FP.
- Tanpa bank integration, status **SUCCESS** berbasis kebijakan (Fast/Safe), **bukan bukti settlement**.

---

## 4) Persona & User Stories
- **Owner/Personal User**: Menggunakan `qriscuy` untuk diri sendiri.  
  - *US-1*: Sebagai user, saya ingin menghasilkan QR (statis/dinamis) yang tetap membayar ke QRIS saya, namun memiliki fingerprint untuk pelacakan invoice.  
  - *US-2*: Sebagai user, saya ingin saat QR discan, invoice saya langsung berubah minimal ke status **SCANNED** dan (opsional, mode Fast) **SUCCESS**.
  - *US-3*: Sebagai user, saya ingin desain QR yang konsisten (logo, label) tanpa mengganggu keterbacaan.

---

## 5) Arsitektur
**Komponen**
- **API Service (FastAPI, Python 3.11)**  
  Endpoint untuk generate QR, terima callback `/scan`, update status, dan (opsional) webhook out.  
- **QR Generator**  
  TLV builder, EMV payload composer, CRC16-CCITT, QR image renderer (Pillow/qrcode).  
- **Scan-Client** (web widget/JS library atau aplikasi POS sederhana)  
  Memanggil `/scan` ketika QR berhasil terbaca (mengirim FP + metadata).  
- **Storage** (SQLite/Postgres)  
  Menyimpan invoices, fingerprints, status transitions, audit log.  
- **Auth**  
  API key per "merchant" (untuk v0.1 single-merchant cukup 1 key).  

**Alur Utama**
1) `POST /v1/qr` → server membuat payload EMV dari payload QRIS user + Tag 62 (FP,SIG,TS) → hitung CRC → render QR → simpan mapping `invoice_id ↔ fp`.  
2) Customer scan QR dengan e-wallet (pembayaran mengalir ke rekening user).  
3) **Scan-Client** mengirim `POST /v1/scan` {fp,sig,ts,device_info} → server verifikasi SIG & TTL → set status `SCANNED`.  
4) **Mode Fast**: langsung set `SUCCESS` (dengan banner peringatan).  
   **Mode Safe**: tetap `PENDING/SCANNED` hingga user **manual confirm** via dashboard/endpoint.  
5) (Opsional) Server kirim webhook `payment.updated` ke sistem user.

---

## 6) Data Model (skema ringkas)
**tables**
- `invoices`
  - `id` (uuid)  
  - `merchant_id` (text)  
  - `amount` (int)  
  - `currency` (text, default IDR)  
  - `status` (enum: `CREATED|SCANNED|SUCCESS|REJECTED|EXPIRED`)  
  - `policy` (enum: `FAST|SAFE`)  
  - `merchant_payload` (text)  
  - `created_at`, `updated_at`
- `fingerprints`
  - `id` (uuid)  
  - `invoice_id` (fk, unique)  
  - `fp_b64` (text)  
  - `sig_hex` (text)  
  - `ts` (int, unix sec)  
  - `nonce` (text)  
  - `ttl_sec` (int, default 300)  
- `scan_events`
  - `id` (uuid)  
  - `invoice_id` (fk)  
  - `device_id` (text, nullable)  
  - `client_meta` (json/text, nullable)  
  - `created_at`

---

## 7) API Design (v1)
### Auth
- `X-API-KEY: <key>` (untuk endpoint generate & admin ops)

### `POST /v1/qr`
Generate QR.
- **Body**
```json
{
  "invoice_id": "INV-20250925-0001",
  "merchant_payload": "<payload_qris_asli_user_or_ref>",
  "amount": 100000,
  "poi_method": "STATIC|DYNAMIC",
  "policy": "FAST|SAFE",
  "ttl_sec": 300,
  "design": { "logo": true, "label": "qriscuy", "size_px": 800 }
}
```
- **Response**
```json
{
  "invoice_id": "...",
  "fp": "...base64...",
  "sig": "...hex...",
  "ts": 1695600000,
  "payload": "<emv_string_with_tag62_and_crc>",
  "qr_png_base64": "data:image/png;base64,...."
}
```

### `POST /v1/scan`
Dipanggil oleh **scan-client** saat QR berhasil dibaca.  
- **Body**
```json
{ "invoice_id": "...", "fp": "...", "sig": "...", "ts": 1695600000,
  "device_id": "pos-01", "agent": "web-qriscuy/1.0" }
```
- **Response**
```json
{ "status": "SCANNED", "policy": "FAST|SAFE", "next": "SUCCESS|WAIT_MANUAL" }
```

### `POST /v1/invoices/{id}/confirm`
Manual confirm (Mode Safe).  
- **Response**: `{ "status": "SUCCESS" }`

### `GET /v1/invoices/{id}`
- **Response**: detail invoice + status + audit trail ringkas.

### Webhook (opsional)
- Event: `payment.updated`  
- Body: `{ invoice_id, status, amount, ts }`

---

## 8) Spesifikasi Payload EMV/QRIS (impl. praktis)
- **Tidak mengubah** field merchant account (routing tetap ke rekening user).  
- Isi minimal yang kita pastikan ada:  
  - `00` (Payload Format Indicator)  
  - `01` (Point of Initiation Method: `11`=static, `12`=dynamic)  
  - `59` (Merchant Name)  
  - `60` (Merchant City)  
  - `26..51` (Merchant Account Info — **tidak diubah**)  
  - `62` (Additional Data Field Template)  
    - Subfield `01`: `FP` (base64)  
    - Subfield `02`: `SIG` (hex HMAC-SHA256)  
    - Subfield `03`: `TS` (unix sec)  
    - Subfield `04`: `ALG` (e.g. `HS256`)  
  - `63` (CRC16-CCITT over payload+`6304`)

> Implementasi mengikuti praktik EMV TLV; penentuan tag/sub‑tag bisa disesuaikan selama konsisten dan tidak mengganggu validator wallet.

---

## 9) Keamanan
- **HMAC-SHA256** dengan secret server untuk menghasilkan `SIG` atas `FP`.  
- `FP` harus memuat: `invoice_id|merchant_id|amount|ts|nonce`.  
- **TTL**: default 300s; tolak `FP` jika `now - ts > ttl`.  
- **Replay**: simpan `nonce` per `invoice_id`; tolak jika pernah dipakai.  
- **API Key** untuk endpoint generate & admin.  
- **Rate limit** `/scan` per `device_id`/IP.  
- **Transport**: HTTPS wajib.

---

## 10) Logging & Observability
- Level: `INFO` default (dapat diatur via env).  
- Formatter JSON kustom menambahkan field tambahan (mis. `method`, `path`, `duration_ms`, `status_code`).  
- Middleware HTTP mencatat setiap request + latency + severity berbasis status code.  
- `ServiceError` menghasilkan log peringatan dengan kode error + route; exception tak tertangani dilog sebagai error dengan stacktrace.  
- Endpoint `/metrics` mengekspor metrik Prometheus:
  - `qriscuy_http_requests_total{method,route,status}`  
  - `qriscuy_http_request_duration_seconds{method,route}`  
  - `qriscuy_service_errors_total{code,route}`  
- Logging memperingatkan bila `API_KEY` atau `HMAC_SECRET` masih nilai default saat startup.

---

## 11) Error Handling & Status
- `CREATED` → setelah QR dibuat.  
- `SCANNED` → `/scan` valid (SIG OK, TTL OK).  
- `SUCCESS` → (Mode Fast: langsung) / (Mode Safe: manual confirm).  
- `EXPIRED` → TTL lewat, tidak ada scan valid.  
- `REJECTED` → manual reject/invalid signature.

**Kode Error umum**
- `ERR_SIG_INVALID`, `ERR_FP_EXPIRED`, `ERR_REPLAY`, `ERR_BAD_PAYLOAD`, `ERR_AUTH`, `ERR_RATE_LIMIT`.

---

## 12) Gaya Perubahan & Protokol Debug (mengikuti PROJECT RULES)
- **Perubahan minimal**: patch kecil, bukan rewrite massal.  
- Setiap patch menyertakan: langkah verifikasi + rencana rollback.  
- **Debug Protocol**:  
  1) Ulangi error dengan jelas.  
  2) Catat environment (`python --version`, lib versions).  
  3) Lampirkan 10–20 baris log terkait.  
  4) Ajukan 2–3 hipotesis penyebab.  
  5) Terapkan patch kecil.  
  6) Verifikasi hasil.

---

## 13) Lingkungan & Cara Run
- **Bahasa**: Python **3.11**  
- **Framework**: FastAPI + Uvicorn  
- **Deps**: `pydantic`, `qrcode`, `Pillow`, `python-dotenv`, `h11`, (opsional) `sqlalchemy`, `sqlite3`

**Struktur Direktori (usulan awal)**
```
qriscuy/
  app/
    api.py            # FastAPI endpoints
    config.py         # env, secrets, mode FAST/SAFE
    tlv.py            # TLV builder/parser
    crc.py            # CRC16-CCITT
    qris_encoder.py   # compose EMV payload + Tag 62 + CRC
    renderer.py       # QR image + desain (logo/label)
    services/
      generator.py    # business logic /v1/qr
      scan.py         # handle /v1/scan
      webhook.py      # webhook out (opsional)
    models.py         # ORM models (SQLite)
    logging_conf.py   # JSON logger
  run.sh
  requirements.txt
  README.md
```

**Run (dev)**
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export QRISCUY_MODE=FAST   # atau SAFE
uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload
```

**Run (prod sederhana)**
```bash
uvicorn app.api:app --host 0.0.0.0 --port 8000 --workers 2
```

---

## 14) Verifikasi (QA Checklist)
1) **Generate** QR: pastikan response mengandung `payload` + `qr_png_base64` + `fp/sig/ts`.  
2) **Decode** QR → cek Tag 62 berisi subfield FP/SIG/TS, merchant fields asli tidak berubah, CRC valid.  
3) **Scan-callback**: panggil `/scan` dengan `fp/sig/ts` valid → status jadi `SCANNED`.  
4) **Mode Fast**: setelah `/scan`, status otomatis `SUCCESS`.  
5) **Mode Safe**: setelah `/scan`, status tetap `SCANNED`; panggil `/confirm` → `SUCCESS`.  
6) **TTL**: coba `/scan` setelah TTL → ditolak `ERR_FP_EXPIRED`.  
7) **Replay**: kirim `/scan` sama 2x → kedua ditolak `ERR_REPLAY`.  
8) **SIG salah**: ditolak `ERR_SIG_INVALID`.

---

## 15) Rollback Plan
- Setiap patch memiliki label release. Jika terjadi regression:  
  1) Rollback container/image ke versi sebelumnya.  
  2) Jalankan migrasi DB rollback jika ada (gunakan migration script terpisah).  
  3) Restore file konfigurasi `.env` dari backup terakhir.  
  4) Verifikasi endpoint `/health` dan test case QA 1–3.

---

## 16) Risiko & Mitigasi
- **False-success (Mode Fast)**: Tanpa bukti mutasi, status sukses hanya asumsi berdasarkan scan-callback.  
  → Sediakan banner peringatan + default **Mode Safe**.  
- **Bypass scan-client**: User memakai scanner lain → tidak ada callback.  
  → Integrasikan scan-client dalam POS/checkout & tampilkan instruksi; sediakan manual confirm.  
- **Wallet drop tag**: Beberapa wallet bisa drop Tag 62.  
  → Uji kompatibilitas di wallet utama (GoPay/OVO/DANA/BRI/mandiri/BCA/ShopeePay).  
- **Security**: FP bisa di-screenshot & dipost ulang (replay).  
  → TTL + nonce + store used-nonce + HMAC.

---

## 17) Open Questions
- Daftar wallet yang akan menjadi **target uji kompatibilitas** minimal?  
- Apakah diperlukan **dashboard** pada v0.1 atau cukup API + CLI?  
- Apakah `merchant_payload` disuplai sebagai **string EMV** atau **gambar QR** yang perlu didecode dulu? (rekomendasi: string EMV untuk presisi)

---

## 18) Lampiran
### 18.1 Fingerprint & Signature
- `FP_RAW = f"{invoice_id}|{merchant_id}|{amount}|{ts}|{nonce}"`  
- `FP_B64 = base64url(FP_RAW)`  
- `SIG = HMAC_SHA256(SECRET, FP_B64)`  
- Validasi: cek waktu (`now - ts <= ttl_sec`), cek replay (`nonce` belum pernah dipakai), cek `hmac.compare_digest`.

### 18.2 CRC16-CCITT
- Polynomial 0x1021, init 0xFFFF.  
- Hitung atas seluruh payload + literal `6304`, kemudian append hasil CRC (big-endian hex) ke tag `63`.

### 18.3 TLV (Tag-Length-Value) builder
- `TAG(2) + LENGTH(2) + VALUE(n)` untuk kesederhanaan (tetap sesuaikan dengan praktik EMV yang berlaku).  
- Subfield Tag 62 menggunakan skema TLV juga (01..,02..,03..).

---

## 19) AI Interaction (dev notes)
- Jika ada error, AI **wajib** jelaskan 2–3 hipotesis penyebab sebelum memberi fix.  
- Dilarang rename/pindah file tanpa permintaan eksplisit.  
- Fokus pada *mengapa* error terjadi, lalu berikan **patch kecil** + cara verifikasi + rollback.

---

**Selesai v0.1** — Siap dioper ke implementasi awal (generator + `/scan`).
