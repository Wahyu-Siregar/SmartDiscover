---
description: Describe when these instructions should be loaded by the agent based on task context
# applyTo: 'Describe when these instructions should be loaded by the agent based on task context' # when provided, instructions will automatically be added to the request context when the pattern matches an attached file
---

<!-- Tip: Use /create-instructions in chat to generate content with agent assistance -->

## ⚠️ Update Penting Spotify API 2025

Sebelum masuk ke arsitektur, perlu diketahui: Spotify **mendeprecate endpoint `/audio-features` dan `/recommendations`** sejak 2025. Alasannya karena Spotify khawatir datanya dipakai untuk training AI model. Ini mengubah sedikit pendekatan project, tapi masih bisa disiasati. [dev](https://dev.to/leemartin/the-state-of-spotify-web-api-report-2025-4gh3)

***

## 🎯 Overview Project

**Nama Project:** *SmartDiscover — Multi-Agent Music Discovery Assistant*

> User cukup mendeskripsikan mood/aktivitas dalam bahasa natural → sistem secara otomatis mencari lagu yang cocok dari Spotify dan menyajikan hasilnya.

***

## 🏗️ Arsitektur 4 Agent

### Agent 1 — Profiler Agent
Tugasnya memahami input user dalam bahasa natural: [scrapegraphai](https://scrapegraphai.com/blog/multi-agent)
- **Input:** Teks bebas dari user, contoh: *"aku mau lagu buat belajar malam, yang tenang dan fokus"*
- **Proses:** LLM mengekstrak parameter: genre, mood, aktivitas, BPM preference, language preference
- **Output:** JSON terstruktur → `{ "mood": "calm", "activity": "studying", "genre": ["lo-fi", "classical", "ambient"], "energy": "low" }`

### Agent 2 — Spotify Search Agent
Menerjemahkan parameter ke query Spotify: [dev](https://dev.to/leemartin/the-state-of-spotify-web-api-report-2025-4gh3)
- **Input:** JSON dari Agent 1
- **Proses:** Pakai endpoint `GET /search` (masih tersedia dan bisa pakai Client Credentials) untuk cari track berdasarkan genre + keyword
- **Output:** Daftar 20–50 kandidat lagu beserta metadata (nama, artis, album, popularity, preview URL)
- **Catatan:** Karena `/recommendations` deprecated, agent ini bisa query multiple keyword variasi untuk memperkaya hasil [dev](https://dev.to/leemartin/the-state-of-spotify-web-api-report-2025-4gh3)

### Agent 3 — Filter & Ranker Agent
Menyaring dan mengurutkan hasil: [scrapegraphai](https://scrapegraphai.com/blog/multi-agent)
- **Input:** Daftar kandidat lagu dari Agent 2
- **Proses:** LLM menilai relevansi tiap lagu berdasarkan nama artis, genre tag, dan popularitas, lalu scoring tiap track
- **Output:** Top 10–15 lagu yang paling relevan, diurutkan berdasarkan score
- **Opsional:** Pakai data dari `GET /artists/{id}` untuk validasi genre artis

### Agent 4 — Presenter Agent
Menyajikan hasil ke user secara rapi: [amarsohail](https://amarsohail.com/blog/multi-agent-orchestration-with-crewai-langgraph-openai-swarm)
- **Input:** Top lagu dari Agent 3
- **Proses:** Format hasil jadi respons yang friendly, tambahkan alasan kenapa lagu ini direkomendasikan
- **Output:** Teks rekomendasi + link Spotify per lagu + embed preview (30 detik via `preview_url`)

***

## 🔁 Flow Diagram

```
User Input (teks)
      ↓
[Agent 1 - Profiler]
   ekstrak: mood, genre, aktivitas
      ↓
[Agent 2 - Spotify Search]
   GET /search → kandidat lagu
      ↓
[Agent 3 - Filter & Ranker]
   scoring & seleksi top lagu
      ↓
[Agent 4 - Presenter]
   format output + preview link
      ↓
Output ke User
```

***

## 🛠️ Tech Stack Rekomendasi

| Komponen | Pilihan |
|---|---|
| **Orchestrasi Agent** | **CrewAI** (lebih simpel untuk pipeline sequential)  [amarsohail](https://amarsohail.com/blog/multi-agent-orchestration-with-crewai-langgraph-openai-swarm) |
| **LLM** | Deepseek / OpenRouter (hemat biaya) |
| **Spotify Client** | `spotipy` library (Python) |
| **Auth Spotify** | Client Credentials Flow (tanpa login user) |
| **Backend** | FastAPI |
| **Frontend** | React / simple HTML+JS |
| **State Management** | LangGraph (opsional, kalau mau flow lebih kompleks)  [dev](https://dev.to/pockit_tools/langgraph-vs-crewai-vs-autogen-the-complete-multi-agent-ai-orchestration-guide-for-2026-2d63) |

Kenapa **CrewAI** untuk project ini? Karena agent-nya punya **peran yang jelas dan linear** (profiling → search → filter → present), cocok dengan sequential process CrewAI. LangGraph lebih cocok kalau ada conditional routing yang kompleks. [dev](https://dev.to/pockit_tools/langgraph-vs-crewai-vs-autogen-the-complete-multi-agent-ai-orchestration-guide-for-2026-2d63)

***

## 📦 Spotify Endpoints yang Dipakai

Semua endpoint ini **masih aktif dan bisa diakses dengan Client Credentials**: [dev](https://dev.to/leemartin/the-state-of-spotify-web-api-report-2025-4gh3)

- `GET /search` — cari lagu berdasarkan keyword + genre
- `GET /tracks/{id}` — detail track
- `GET /artists/{id}` — validasi genre artis
- `GET /browse/categories` — kategori musik tersedia
- `preview_url` dari response track — audio preview 30 detik gratis

***

