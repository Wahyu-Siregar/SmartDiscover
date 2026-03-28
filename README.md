<div align="center">
  <img src="web/assets/logo.svg" alt="SmartDiscover Logo" width="180"/>
  <h1>✨ SmartDiscover</h1>
  <p><strong>Bawa Musikmu ke Level Berikutnya dengan AI Multi-Agent</strong></p>

  [![Python Validation](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](#)
  [![FastAPI Backbone](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](#)
  [![Vanilla JS Frontend](https://img.shields.io/badge/Magic_UI-000000?style=for-the-badge&logo=css3&logoColor=white)](#)
  [![Spotify API Integration](https://img.shields.io/badge/Spotify_API-1DB954?style=for-the-badge&logo=spotify&logoColor=white)](#)
  [![OpenRouter LLM](https://img.shields.io/badge/OpenRouter-Multi_Agent-purple?style=for-the-badge)](#)
</div>

---

> 🎵 *“Aku mau lagu belajar malam yang tenang dan fokus...”*
> Boom! Daftar putar (*playlist*) seketika terbuat langsung di akun Spotify kamu.

**SmartDiscover** adalah mesin kurasi musik inovatif bertenaga *Multi-Agent AI*. Sistem ini beroperasi selayaknya produser musik pribadimu: ia menerjemahkan kalimat bebas *(natural language)* menjadi tatanan arsitektur mood, menggali perpustakaan API Spotify, dan membuang lagu yang tidak relevan untuk dirakit menjadi satu *playlist* yang sempurna.

## 🚀 Bagaimana Otak AI Ini Bekerja? (The 4-Agent Pipeline)

Arsitektur kami dibangun dengan membagi beban kognitif ke 4 Agen terspesialisasi:

1. 🧠 **Profiler Agent**: Membedah kalimatmu. Dia tahu bedanya "lagu lari pagi" dengan "lagu menangis di pojokan kamar".
2. 🔍 **Spotify Search Agent**: (BARU!) Menambang lagu secara organik lewat *User Playlist* Spotify (bukan sekadar cari judul lagu) sehingga *vibes* yang didapat dijamin *human-curated*, tidak ada lagu repetitif berdasarkan judul harafiah lagi.
3. ⚖️ **Filter & Ranker Agent**: Kurator teliti yang menilai setiap lagu tunggal, mencoret artis *spam*, dan memberikan skor persentase keakuratan tiap lagu untuk *mood*-mu.
4. 🎁 **Presenter Agent**: Merangkum hasil temuan dan mengemasnya dalam antarmuka UI *Bento Grid* siap ekspor!

## ✨ Tampilan Web "Magic UI"
Sistem sudah dilengkapi dengan antarmuka memukau bergaya retro menggunakan palet komponen *UI Layout Modern*.
- 🖥️ **Bento Grid Layout**: Desain asimetris namun minimalis & bersih.
- 🌠 **Shimmer & Glow Cards**: Efek pendaran mouse mengikuti kursor tiap kali kamu melihat profil lagu.
- 👾 **Live Pixel Tracker**: Lacak kerja Agen AI dengan indikator animasi sprite (Si kecil Pixel Agent berjalan melintasi *pipeline*!)

---

## 🛠️ Panduan Instalasi Global (Open Source Setup)

Karena fungsionalitas utama (*Generate Playlist*) membutuhkan akses resmi Spotify ke akunmu sendiri, ikuti 3 langkah mudah ini:

### 1. Buat Aplikasi di Akun Spotify Developer
Kamu butuh *Kunci Akses* agar AI punya wewenang membuatkan playlist untukmu.
- Kunjungi [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
- Masuk / Register, lalu buat aplikasi baru (*Create App*). Isi bebas namanya.
- Di dalam App tersebut, buka **"Settings"**.
- Temukan kolom **Redirect URIs**, dan masukkan persis teks ini: 
  👉 http://127.0.0.1:8000/auth/callback 
- Lalu tekan **Add**, *scroll* ke bawah dan klik **Save**.
- Jangan tutup halaman ini, catat nilai **Client ID** dan **Client Secret** kamu.

### 2. Unduh Code & Siapkan Environment
Buka terminal OS / shell kesukaanmu, eksekusi perintah kloning dan instalasi berikut:

``powershell
# 1. Kloning repo
git clone https://github.com/wahyu-shiregaru/SmartDiscover.git
cd SmartDiscover

# 2. Buat lingkungan virtual terisolasi
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # (Bagi pengguna Windows)
# source .venv/bin/activate    # (Bagi pengguna Mac/Linux)

# 3. Instal semua requirements (FastAPI, httpx, dll)
pip install -r requirements.txt

# 4. Copy template lingkungan kerja (Environment)
cp .env.example .env
``

### 3. Setup Kunci Rahasiamu (.env)
Buka *Code Editor*-mu (seperti VS Code), lalu buka *file* .env yang baru saja tercetak dari *copy* instalasi poin no 4 tadi.
Di sana tempat kosong sudah aku siapkan. Isi semua tokennya (Spotify yang barusan didapat + OpenRouter AI):

`ini
OPENROUTER_API_KEY="sk-or-v1-apikey-kamu..."
SPOTIFY_CLIENT_ID="d8be....dari-dashboard-kamu"
SPOTIFY_CLIENT_SECRET="a449....client-secret-kamu"
`

### 4. Nyalakan Turbin! 🚀
Setelah disave, nyalakan *server websocket* nya dengan mengeksekusi ini di terminal:
`powershell
uvicorn app.main:app --reload
`

> **🌐 Dashboard Lokal** sudah *live* sekarang. Akses lewat browser dengan klik: 
> 👉 [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

## 🛡️ Jaminan Fallback (Anti-Patah)
Jangan khawatir tentang error jika kamu tak sengaja salah masukkin kredensial tadi, SmartDiscover difiturkan anti-patah algoritma.
- **Kamu belum masukkan Spotify Keys di .env?** Dashboard UI kamu tidak akan hancur dan *crash*, SmartDiscover akan otomatis "beralih" mode menjadi versi *Mock Candidates Mode* sekadar agar antarmuka Pixel Tracker tetap bisa kamu demonstrasikan! (Sangat direkomendasikan bagi Front-End Enginners).


<div align="center">
  <br>
  <i>Dirancang teliti dengan dedikasi AI Algoritma.</i>
</div>
