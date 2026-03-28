---
name: smartdiscover-recommendation-pipeline
description: 'Bangun rekomendasi lagu SmartDiscover end-to-end dari prompt natural language dengan alur 4-agent (profiler, spotify search, filter-ranker, presenter). Gunakan saat user minta rekomendasi lagu berbasis mood/aktivitas, termasuk fallback query bila hasil Spotify minim.'
argument-hint: 'Masukkan intent user, constraint (bahasa, genre, durasi), dan format output yang diinginkan.'
user-invocable: true
---

# SmartDiscover Recommendation Pipeline

## Tujuan
Skill ini menghasilkan rekomendasi lagu yang relevan dari input natural language user melalui alur terstruktur 4 tahap:
1. Profiler Agent
2. Spotify Search Agent
3. Filter and Ranker Agent
4. Presenter Agent

Output akhir: daftar rekomendasi lagu yang dapat dijelaskan alasannya, siap ditampilkan ke user.

## Kapan Dipakai
- User menulis intent bebas, misalnya: "lagu buat fokus kerja malam"
- User ingin rekomendasi berbasis mood, aktivitas, atau vibe
- Sistem perlu fallback karena endpoint Spotify `/recommendations` tidak tersedia
- Diperlukan output konsisten untuk UI/API

## Input Minimum
- Teks intent user
- Batasan opsional: bahasa, genre, level energi, rentang popularitas, jumlah hasil

Aturan bahasa:
- Bahasa output mengikuti bahasa input user secara default.
- Jika user mencampur bahasa, gunakan bahasa dominan di input dan pertahankan istilah musik yang umum.

## Prosedur
1. Normalisasi intent user.
2. Jalankan Profiler Agent untuk ekstraksi atribut.
3. Validasi hasil profiling.
4. Jalankan Spotify Search Agent dengan query multivarian.
5. Cek kualitas kandidat hasil pencarian.
6. Jalankan Filter and Ranker Agent.
7. Terapkan quality gate ranking.
8. Jalankan Presenter Agent untuk format output final.
9. Validasi final response sebelum dikirim.

## Detail Tahap

### 1) Profiler Agent
Konversi teks user ke JSON terstruktur.

Target struktur minimal:
```json
{
  "mood": "calm",
  "activity": "studying",
  "genre": ["lo-fi", "ambient"],
  "energy": "low",
  "language": "id"
}
```

Quality check:
- Wajib punya `mood` atau `activity`
- `genre` boleh kosong, tapi jika ada harus array
- Nilai abstrak (mis. "chill banget") diturunkan ke label operasional (mis. `energy: low`)

### 2) Spotify Search Agent
Gunakan endpoint aktif saja:
- `GET /search`
- `GET /tracks/{id}`
- `GET /artists/{id}` (opsional validasi genre artis)

Strategi query:
- Buat 3-6 variasi keyword dari kombinasi mood, activity, genre
- Campur query sempit (presisi) dan query lebar (recall)
- Ambil 20-50 kandidat total

Decision points:
- Jika hasil < 15 kandidat: longgarkan genre, pertahankan mood/activity
- Jika hasil terlalu homogen: tambahkan variasi artis/keyword lintas subgenre
- Jika `preview_url` minim: prioritaskan track dengan metadata paling lengkap

### 3) Filter and Ranker Agent
Skor kandidat berdasarkan:
- Kecocokan semantic terhadap intent
- Konsistensi mood/energi
- Popularitas (sebagai sinyal sekunder)
- Keragaman artis/genre ringan agar tidak monoton

Contoh skema skor:
- Relevansi intent: 50%
- Mood-energy fit: 25%
- Popularitas: 15%
- Diversity bonus: 10%

Quality gate ranking:
- Buang kandidat duplikat judul-artis
- Target default 15 lagu lolos jika kandidat memungkinkan
- Top hasil harus menyertakan alasan singkat kenapa dipilih

### 4) Presenter Agent
Format output ramah user:
- Ringkasan 1-2 kalimat sesuai intent
- Daftar top 15 lagu (default)
- Tiap item: judul, artis, alasan, link Spotify, status preview

Format item rekomendasi:
```json
{
  "title": "...",
  "artist": "...",
  "spotify_url": "...",
  "preview_url": "...",
  "why": "tempo stabil dan nuansa tenang untuk fokus"
}
```

## Fallback dan Branching
- Jika profiling ambigu: minta klarifikasi singkat maksimal 2 pertanyaan jika intent sangat ambigu. Prioritaskan pertanyaan dengan dampak terbesar ke hasil (contoh: "mau yang instrumental atau vokal?").
- Jika hasil pencarian rendah: jalankan ulang search dengan query lebih umum
- Jika hasil tetap rendah: tampilkan hasil terbaik yang ada + jelaskan keterbatasan
- Jika user minta regenerasi: pertahankan intent inti, ubah keragaman artis/genre

## Definisi Selesai
Skill dianggap selesai bila:
1. Output final relevan dengan intent user.
2. Target default 15 rekomendasi tersedia (atau alasan jelas bila kurang).
3. Setiap lagu punya alasan pemilihan singkat.
4. Tidak menggunakan endpoint Spotify deprecated.
5. Respons siap pakai untuk UI/API.

## Prompt Contoh
- /smartdiscover-recommendation-pipeline "aku mau lagu buat belajar malam yang tenang dan fokus"
- /smartdiscover-recommendation-pipeline "butuh lagu lari pagi, energik, campuran lokal dan internasional"
