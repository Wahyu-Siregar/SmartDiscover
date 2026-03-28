<div align="center">
  <img src="web/assets/logo.svg" alt="SmartDiscover Logo" width="180"/>
  <h1>✨ SmartDiscover</h1>
  <p><strong>Multi-Agent Music Discovery Assistant</strong></p>

  [![Python Validation](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python&logoColor=white)](#)
  [![FastAPI Backbone](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](#)
  [![Vanilla JS Frontend](https://img.shields.io/badge/Vanilla_JS-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)](#)
  [![Spotify API Integration](https://img.shields.io/badge/Spotify_API-1DB954?style=for-the-badge&logo=spotify&logoColor=white)](#)
  [![OpenRouter LLM](https://img.shields.io/badge/OpenRouter-Multi_Agent-purple?style=for-the-badge)](#)
</div>

---

SmartDiscover adalah MVP backend cerdas untuk *Multi-Agent Music Discovery Assistant*. Sistem ini bekerja layaknya asisten musik pribadimu: meracik rekomendasi lagu berbasis konteks dengan membagi tugas ke **4 spesialis agen** untuk menghasilkan daftar akhir lagu yang akurat, relevan, dan terpersonalisasi.

## 🚀 Alur Kerja Multi-Agent
1. 🧠 **Profiler Agent**: Mengekstraksi mood, aktivitas, dan konteks linguistik murni dari kalimat instruksi pengguna.
2. 🔍 **Spotify Search Agent**: Menarik kandidat lagu multi-kueri langsung dari Spotify menggunakan penyesuaian parameter (*search broadening*).
3. ⚖️ **Filter & Ranker Agent**: Mengevaluasi kandidat lagu, mencegah spam artis, dan memberikan skor relevansi dinamis.
4. 🎁 **Presenter Agent**: Merangkum hasil temuan, menyusun hasil kurasi terbaik menjadi struktur playlist API final.

## ✨ Fitur Utama
- 🎯 **Endpoint Presisi:** POST /recommend menghasilkan *Output JSON Schema* yang kokoh tanpa *hallucinations*.
- ⚡ **Diagnostics Tools:** Cek performa independen (/health, /spotify/health, /llm/health).
- 🖥️ **Live Web Dashboard:** UI responsif bersih dengan antarmuka lintasan agen yang beranimasi seketika (_Realtime Pixel tracking_).
- 🛡️ **Resilient Fallback:** Mendukung *Mock Candidates* saat kredensial Spotify absen, serta *Heuristic Rule-matching* otomatis saat layanan LLM terputus.
- 🚫 **Modern Endpointing:** Bebas limitasi API kadaluarsa (Tidak lagi bergantung pada /recommendations API lawas).

## 🛠️ Cara Setup & Run Singkat

**1. Buat Virtual Environment & Install Dependensi**
`powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
`

**2. Siapkan Environment Variables**
Salin \.env.example\ menjadi \.env\.
`powershell
Copy-Item .env.example .env
`

**3. Nyalakan Engine 🚀**
`powershell
uvicorn app.main:app --reload
`

> **🌐 Tautan Lokal:**
> - Web Interaktif (Dashboard): [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
> - Struktur API / Dokumentasi Swagger: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 📝 Demo Request API

**Contoh Payload POST \/recommend\:**
`http
POST /recommend
Content-Type: application/json

{
  "text": "aku mau lagu buat belajar malam yang tenang dan fokus",
  "target_count": 15
}
`

**Cuplikan Struktur JSON (Response):**
`json
{
  "summary": { "input_language": "id", "returned_count": 15 },
  "intent_profile": { "mood": "calm", "activity": "studying", "energy": "low" },
  "recommendations": [
    {
      "rank": 1,
      "title": "Midnight Focus",
      "artist": "Loftline",
      "why": "Cocok untuk studying dengan nuansa calm dan energi low.",
      "score": 0.412
    }
  ]
}
`

---

## 🔑 Konfigurasi Rahasia (\.env\)

| Ekosistem API | Variabel Kunci | Peran / Nilai Awal |
|---|---|---|
| **Spotify Search** | \SPOTIFY_CLIENT_ID\ <br> \SPOTIFY_CLIENT_SECRET\ | Akses *realtime data* Spotify. Jika kosong akan dialihkan ke mode *Mock Candidates*. |
| **OpenRouter Engine** | \OPENROUTER_API_KEY\<br>\OPENROUTER_MODEL\<br>\OPENROUTER_BASE_URL\ | Mengaktivasikan otak LLM untuk Pipeline Agent. (Default: \google/gemini-2.5-flash-lite\). |

