

# 🚀 qriscuy


Generator QRIS dengan fingerprint **in-QR** berbasis FastAPI (Python 3.11). ⚡

- Python 3.11 (disarankan via [pyenv](https://github.com/pyenv/pyenv) atau installer resmi)
- Git
- (Opsional) Docker 24+

## 🛠️ Persyaratan
- 🐍 Python 3.11 (disarankan via [pyenv](https://github.com/pyenv/pyenv) atau installer resmi)
- 🌀 Git
- 🐳 (Opsional) Docker 24+
- Python 3.11 (disarankan via [pyenv](https://github.com/pyenv/pyenv) atau installer resmi)
- Git
- (Opsional) Docker 24+


## 📚 Panduan Lengkap (Beginner Friendly)

### 1. Clone Repositori 🌀
```bash
git clone https://github.com/moccalatte/qriscuy.git
cd qriscuy
```

### 2. Cek & Siapkan Python 3.11 🐍
- **Rekomendasi:** gunakan [pyenv](https://github.com/pyenv/pyenv)
```bash
pyenv install 3.11.9  # jika belum ada
pyenv local 3.11.9
```
Atau pastikan `python3.11 --version` mengembalikan 3.11.x


### 3. Siapkan Konfigurasi Lingkungan 🔑
- Salin file contoh:
   ```bash
   cp .env.example .env
   ```
- Edit `.env` sesuai kebutuhan (ganti semua nilai rahasia sebelum ke produksi).

### 4. Jalankan Aplikasi (Mode Pengembangan) 🚦
```bash
PYTHON_BIN=$(pyenv which python3.11 2>/dev/null || command -v python3.11)
QRISCUY_MODE=SAFE ./run.sh
```
Perintah di atas otomatis:
- Membuat virtualenv `.venv`
- Install dependensi dari `requirements.txt`
- Menjalankan Uvicorn di `http://0.0.0.0:8000`

### 5. Uji Koneksi Cepat 🩺
```bash
curl http://localhost:8000/health
```
Jika sukses, akan mendapat response status OK.

### 6. Struktur Folder Penting 📁
- `app/` — kode utama FastAPI, encoder, renderer, dsb
- `services/` — logika generator, scan, error
- `run.sh` — script utama jalankan server
- `.gitignore` — sudah disiapkan, aman untuk push ke GitHub

### 7. Jalankan dengan Docker (Opsional) 🐳
```bash
docker build -t qriscuy .
docker run --rm -p 8000:8000 --env-file .env qriscuy
```

### 8. Catatan Project Rules 📏
- Semua error/log dicatat jelas (lihat `project_rules.md`) 📝
- Tidak ada perubahan besar tanpa permintaan eksplisit 🚫
- File/fungsi harus single responsibility 🧩
- Rollback mudah: cukup checkout commit sebelumnya ⏪

---



---

🔎 Lihat `prd_qriscuy.md` untuk detail fitur & scope.
🧑‍💻 Lihat `project_rules.md` untuk aturan kontribusi & debugging.

---

## 🚦 Jalankan & Uji API

1. **Cek status server**
   ```bash
   curl -H "X-API-Key: ubah-api-key" http://localhost:8000/health
   ```
   Jika sukses, akan mendapat response status OK.

2. **Jelajahi API**
   - Dokumentasi interaktif: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Endpoint metrics Prometheus: [http://localhost:8000/metrics](http://localhost:8000/metrics)

3. **Hentikan server**
   - Tekan `Ctrl+C` pada terminal yang menjalankan `run.sh`.

> **Catatan**: Jika `PYTHON_BIN` tidak mengarah ke Python 3.11, script akan berhenti dan meminta Anda memasang versi yang benar.

---

## 🔑 Variabel Lingkungan Penting

| Nama             | Keterangan                                                                 |
|------------------|----------------------------------------------------------------------------|
| `API_KEY`        | Digunakan untuk header `X-API-Key` (WAJIB diganti di produksi)             |
| `HMAC_SECRET`    | Kunci HMAC untuk tanda tangan fingerprint (WAJIB diganti)                  |
| `QRISCUY_MODE`   | `FAST` atau `SAFE`                                                         |
| `DATABASE_URL`   | Default SQLite lokal (`sqlite+aiosqlite:///./qriscuy.db`). Untuk Docker: `/app/data/qriscuy.db` |
| `ALLOWED_ORIGINS`| Daftar CORS (JSON array) jika menggunakan frontend berbeda domain          |

---

## 📡 Endpoint Utama

- `POST /v1/qr` — generate invoice + QR baru dengan Tag 62 fingerprint & signature
- `POST /v1/scan` — callback ketika QR discan oleh client terkendali
- `GET /v1/invoices/{id}` — cek status invoice
- `POST /v1/invoices/{id}/confirm` — konfirmasi manual (mode SAFE) menjadi `SUCCESS` atau `REJECTED`
- `GET /health` — health check sederhana

---

## 🔄 Alur Singkat

1. User kirim payload QRIS asli ke `/v1/qr` → sistem menyisipkan Tag 62 (`FP`, `SIG`, `TS`, `ALG`)
2. Client pemindai mengirim `/v1/scan` dengan fingerprint & signature
3. Mode `FAST` → invoice otomatis `SUCCESS`. Mode `SAFE` → status tetap `SCANNED` hingga konfirmasi manual

---

## 📝 Verifikasi Manual

1. `POST /v1/qr` → pastikan respons memuat `payload`, `qr_png_base64`, `fingerprint_b64`, `signature_hex`, `crc`
2. Decode `payload` dan cek Tag 62 berisi sub-tag `01..05`, CRC valid
3. `POST /v1/scan` dengan data respons tahap 1 → status berubah (`SCANNED` atau `SUCCESS` tergantung mode)
4. Mode `SAFE`: panggil `/v1/invoices/{id}/confirm` dengan `{"action":"SUCCESS"}` → status `SUCCESS`
5. Uji TTL: tunggu > `settings.ttl_seconds` lalu ulangi `/v1/scan` → respon error `ERR_FP_EXPIRED`
6. Uji replay: kirim `/v1/scan` dua kali berturut → panggilan kedua mengembalikan `ERR_REPLAY`

---

## ⏪ Rencana Rollback

- Hentikan proses `uvicorn` berjalan
- Restore backup file konfigurasi dan database `qriscuy.db` (atau hapus untuk reset)
- Jalankan ulang `./run.sh` untuk memastikan semua dependensi bersih

---

## 📊 Monitoring & Observability

- Semua request dicatat dalam log JSON (`logger` `qriscuy.http` dan `qriscuy.api`) beserta status kode dan durasi
- Kesalahan layanan (`ServiceError`) serta exception lain otomatis tercatat dengan stack trace
- Endpoint `GET /metrics` mengekspor metrik Prometheus (`qriscuy_http_requests_total`, `qriscuy_http_request_duration_seconds`, `qriscuy_service_errors_total`). Integrasikan dengan Prometheus atau cek cepat via `curl localhost:8000/metrics`

## Deploy via Docker
1. **Build image**
   ```bash
   docker build -t qriscuy:latest .
   ```
2. **Menjalankan container**
   ```bash
   docker run -d \
     --name qriscuy \
     -p 8000:8000 \
     -e API_KEY="ubah-api-key" \
     -e HMAC_SECRET="ubah-hmac-secret" \
     -e QRISCUY_MODE="SAFE" \
     -e DATABASE_URL="sqlite+aiosqlite:///data/qriscuy.db" \
     -v $(pwd)/data:/app/data \
     qriscuy:latest
   ```
   - Direktori `$(pwd)/data` menyimpan database SQLite secara persisten.
   - Untuk mengaktifkan CORS khusus, set `ALLOWED_ORIGINS`, misal `['https://qriscuy.potion.my.id']`.

### Integrasi Domain via cloudflared
Misal Anda ingin mengarahkan `https://qriscuy.potion.my.id` ke container lokal melalui Cloudflare Tunnel:
```bash
docker run -d \
  --name cloudflared \
  --network host \
  -v $HOME/.cloudflared:/etc/cloudflared \
  cloudflare/cloudflared:latest tunnel run <NAMA_TUNNEL>
```
- Pastikan tunnel mem-forward ke `http://localhost:8000` (atau host/port sesuai `docker run`).
- Atur CNAME di Cloudflare dashboard untuk `qriscuy.potion.my.id` → `<UUID>.cfargotunnel.com`.
- Setelah tunnel aktif, domain akan proxy ke layanan FastAPI yang berjalan di container.
