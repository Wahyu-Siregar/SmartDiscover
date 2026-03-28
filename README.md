# SmartDiscover

SmartDiscover adalah aplikasi rekomendasi musik berbasis Multi-Agent AI. User cukup menulis kebutuhan musik dalam bahasa natural, lalu sistem akan mencari kandidat lagu dari Spotify, memfilter hasil, dan menampilkan rekomendasi terbaik.

## Fitur Utama

- Arsitektur 4 agent: profiler, spotify search, filter-ranker, presenter.
- Integrasi Spotify untuk pencarian kandidat lagu.
- UI web untuk menjalankan flow rekomendasi.
- Dukungan ekspor hasil ke playlist Spotify (saat kredensial tersedia).

## Arsitektur Pipeline

1. Profiler Agent
   - Mengekstrak intent, mood, konteks aktivitas, dan preferensi musik dari prompt user.
2. Spotify Search Agent
   - Mencari kandidat lagu menggunakan query yang relevan dari hasil profiling.
3. Filter and Ranker Agent
   - Menyaring kandidat dan memberi skor relevansi.
4. Presenter Agent
   - Menyusun hasil akhir agar mudah dipahami user.

## Setup Cepat

### 1) Buat aplikasi di Spotify Developer

- Buka: https://developer.spotify.com/dashboard
- Buat app baru.
- Isi Redirect URI berikut:

```text
http://127.0.0.1:8000/auth/callback
```

- Simpan Client ID dan Client Secret.

### 2) Clone repo dan install dependency

```powershell
git clone https://github.com/wahyu-shiregaru/SmartDiscover.git
cd SmartDiscover

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
Copy-Item .env.example .env
```

Untuk macOS/Linux:

```bash
source .venv/bin/activate
cp .env.example .env
```

### 3) Isi file .env

```ini
OPENROUTER_API_KEY="sk-or-v1-apikey-kamu..."
SPOTIFY_CLIENT_ID="d8be....dari-dashboard-kamu"
SPOTIFY_CLIENT_SECRET="a449....client-secret-kamu"
```

### 4) Jalankan server

```powershell
uvicorn app.main:app --reload
```

Buka aplikasi di:

- http://127.0.0.1:8000/

## Fallback Behavior

Jika kredensial Spotify belum valid/tersedia, aplikasi tetap berjalan dalam mode fallback agar UI tetap bisa didemokan.

## Lisensi

Project ini menggunakan MIT License. Lihat file LICENSE.

## Legal Disclaimer

- Aplikasi ini menggunakan API pihak ketiga (Spotify dan provider LLM eksternal).
- Proyek ini independen dan tidak berafiliasi, disponsori, atau didukung resmi oleh Spotify.
- Seluruh merek dagang, logo, dan aset Spotify adalah milik Spotify AB.
- Penggunaan API key wajib mengikuti Terms of Service penyedia terkait.

## Maintainer

Copyright (c) 2026 wahyu muliadi siregar
