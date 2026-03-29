const form = document.getElementById("recommendForm");
const intentInput = document.getElementById("intentInput");
const targetCountInput = document.getElementById("targetCountInput");
const submitBtn = document.getElementById("submitBtn");
const healthBtn = document.getElementById("healthBtn");
const spotifyLoginBtn = document.getElementById("spotifyLoginBtn");
const llmBadge = document.getElementById("llmBadge");
const spotifyBadge = document.getElementById("spotifyBadge");
const quickPrompts = document.getElementById("quickPrompts");
const statusText = document.getElementById("statusText");
const recommendationList = document.getElementById("recommendationList");
const resultLead = document.getElementById("resultLead");
const summaryMood = document.getElementById("summaryMood");
const summaryActivity = document.getElementById("summaryActivity");
const summaryCount = document.getElementById("summaryCount");
const summaryMode = document.getElementById("summaryMode");
const agentFlow = document.getElementById("agentFlow");
const agentStageText = document.getElementById("agentStageText");
const agentMetrics = document.getElementById("agentMetrics");
const pipelinePanel = document.querySelector(".pipeline-panel");
const trackContainer = document.querySelector(".track-container");
const trackActive = document.querySelector(".track-active");
const pillProfiler = document.getElementById("pillProfiler");
const pillSearch = document.getElementById("pillSearch");
const pillRanker = document.getElementById("pillRanker");
const pillPresenter = document.getElementById("pillPresenter");

let agentStageTimer = null;
let replayToken = 0;
const stagePills = [pillProfiler, pillSearch, pillRanker, pillPresenter];
const agentPixel = document.getElementById("agentPixel");

let runtimeFrameTimer = null;
let runtimeFrameIndex = 0;
let runtimeVisualState = "idle";
let lastRuntimeFrameAt = 0;
let currentRuntimeFrameSrc = "";
let currentPreviewAudio = null;
let currentPreviewButton = null;

const prefersReducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
const coarsePointerQuery = window.matchMedia("(pointer: coarse)");

function getRuntimeFrameIntervalMs() {
  if (prefersReducedMotionQuery.matches) return 240;
  if (coarsePointerQuery.matches) return 160;
  return 120;
}

let runtimeFrameIntervalMs = getRuntimeFrameIntervalMs();

const RUNTIME_FRAME_SETS = {
  idle: ["/static/assets/runtime/idle-1.svg", "/static/assets/runtime/idle-2.svg"],
  profiler: ["/static/assets/runtime/profiler-1.svg", "/static/assets/runtime/profiler-2.svg", "/static/assets/runtime/profiler-3.svg"],
  search: ["/static/assets/runtime/search-1.svg", "/static/assets/runtime/search-2.svg", "/static/assets/runtime/search-3.svg"],
  ranker: ["/static/assets/runtime/ranker-1.svg", "/static/assets/runtime/ranker-2.svg", "/static/assets/runtime/ranker-3.svg"],
  presenter: ["/static/assets/runtime/presenter-1.svg", "/static/assets/runtime/presenter-2.svg", "/static/assets/runtime/presenter-3.svg"],
  done: ["/static/assets/runtime/done-1.svg", "/static/assets/runtime/done-2.svg"],
  error: ["/static/assets/runtime/error-1.svg", "/static/assets/runtime/error-2.svg"],
};

const ALL_RUNTIME_FRAMES = Array.from(new Set(Object.values(RUNTIME_FRAME_SETS).flat()));
let runtimeFramesPreloaded = false;

function preloadRuntimeFrames() {
  if (runtimeFramesPreloaded) return;
  runtimeFramesPreloaded = true;

  for (const src of ALL_RUNTIME_FRAMES) {
    const img = new Image();
    img.src = src;
  }
}

function renderRuntimeFrame() {
  if (!agentPixel) return;
  const frames = RUNTIME_FRAME_SETS[runtimeVisualState] || RUNTIME_FRAME_SETS.idle;
  const frame = frames[runtimeFrameIndex % frames.length];
  if (currentRuntimeFrameSrc !== frame) {
    agentPixel.setAttribute("src", frame);
    currentRuntimeFrameSrc = frame;
  }
  runtimeFrameIndex = (runtimeFrameIndex + 1) % frames.length;
}

function runtimeFrameTick(timestamp) {
  if (!lastRuntimeFrameAt || (timestamp - lastRuntimeFrameAt) >= runtimeFrameIntervalMs) {
    renderRuntimeFrame();
    lastRuntimeFrameAt = timestamp;
  }
  runtimeFrameTimer = requestAnimationFrame(runtimeFrameTick);
}

function bindRuntimePreferences() {
  const syncInterval = () => {
    runtimeFrameIntervalMs = getRuntimeFrameIntervalMs();
  };

  prefersReducedMotionQuery.addEventListener("change", syncInterval);
  coarsePointerQuery.addEventListener("change", syncInterval);
}

function startRuntimeFrameLoop() {
  preloadRuntimeFrames();
  if (runtimeFrameTimer) cancelAnimationFrame(runtimeFrameTimer);
  lastRuntimeFrameAt = 0;
  runtimeFrameTimer = requestAnimationFrame(runtimeFrameTick);
}

function setStatus(message, isError = false) {
  statusText.textContent = message;
  statusText.style.color = isError ? "#ff8f8f" : "#a2cad4";
}

function setLlmBadge(text, tone = "neutral") {
  llmBadge.classList.remove("neutral", "ok", "warn", "error");
  llmBadge.classList.add(tone);
  llmBadge.textContent = text;
}

function setSpotifyBadge(text, tone = "neutral") {
  spotifyBadge.classList.remove("neutral", "ok", "warn", "error");
  spotifyBadge.classList.add(tone);
  spotifyBadge.textContent = text;
}

function setAgentStage(stage, text) {
  agentFlow.dataset.stage = String(stage);
  agentStageText.textContent = text;
  const visualByStage = {
    0: "idle",
    1: "profiler",
    2: "search",
    3: "ranker",
    4: "presenter",
  };
  setRuntimeVisualState(visualByStage[stage] || "idle");
  stagePills.forEach((pill, index) => {
    const n = index + 1;
    pill.classList.toggle("active", n === stage);
    pill.classList.toggle("done", stage > 0 && n < stage);
  });
  syncPipelineGeometry(stage);
}

function getDotCenterX(pill, containerRect) {
  const dot = pill?.querySelector?.(".dot");
  if (!dot) return null;
  const dotRect = dot.getBoundingClientRect();
  return dotRect.left - containerRect.left + (dotRect.width / 2);
}

function syncPipelineGeometry(stage) {
  if (!trackContainer || !agentPixel || !trackActive) return;

  const containerRect = trackContainer.getBoundingClientRect();
  const dotCenters = stagePills
    .map((pill) => getDotCenterX(pill, containerRect))
    .filter((value) => typeof value === "number");

  if (!dotCenters.length) return;

  let targetX = 0;
  if (stage <= 0) {
    if (dotCenters.length > 1) {
      const lead = dotCenters[1] - dotCenters[0];
      targetX = Math.max(0, dotCenters[0] - (lead * 0.6));
    } else {
      targetX = Math.max(0, dotCenters[0] - 18);
    }
  } else {
    targetX = dotCenters[Math.min(stage - 1, dotCenters.length - 1)];
  }

  agentPixel.style.left = `${targetX}px`;
  trackActive.style.width = `${Math.max(0, targetX)}px`;
}

function bindPipelineGeometrySync() {
  let rafId = 0;
  const resync = () => {
    if (rafId) cancelAnimationFrame(rafId);
    rafId = requestAnimationFrame(() => {
      const stage = Number(agentFlow?.dataset?.stage || 0);
      syncPipelineGeometry(Number.isFinite(stage) ? stage : 0);
    });
  };

  window.addEventListener("resize", resync, { passive: true });
  resync();
}

function setAgentMetrics(text) {
  agentMetrics.textContent = text;
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function setRuntimeVisualState(state) {
  if (pipelinePanel) {
    if (state === "error") {
      pipelinePanel.style.borderColor = "var(--brand-glow)";
    } else {
      pipelinePanel.style.borderColor = "var(--border-color)";
    }
  }
  if (runtimeVisualState !== state) {
    runtimeVisualState = state;
    runtimeFrameIndex = 0;
    renderRuntimeFrame();
  }
}

async function replayStagesFromMetrics(stageMs) {
  const token = ++replayToken;
  const sequence = [
    [1, "Profiler Agent • Memahami mood dan aktivitas", Number(stageMs?.profiler || 0)],
    [2, "Spotify Search Agent • Menelusuri kandidat lagu", Number(stageMs?.search || 0)],
    [3, "Filter & Ranker Agent • Menilai relevansi", Number(stageMs?.ranker || 0)],
    [4, "Presenter Agent • Menyusun hasil terbaik", Number(stageMs?.presenter || 0)],
  ];

  agentFlow.classList.add("is-working");
  agentFlow.classList.remove("is-done");

  for (const [stage, label, rawMs] of sequence) {
    if (token !== replayToken) {
      return;
    }
    setAgentStage(stage, label);
    const waitMs = Math.min(1600, Math.max(320, rawMs));
    await delay(waitMs);
  }

  if (token !== replayToken) {
    return;
  }
  agentFlow.classList.remove("is-working");
  agentFlow.classList.add("is-done");
  setAgentStage(4, "Selesai • Playlist siap diputar");
  setRuntimeVisualState("done");
}

function stopAgentAnimation(isSuccess, stageMs = null) {
  replayToken += 1;
  if (agentStageTimer) {
    clearInterval(agentStageTimer);
    agentStageTimer = null;
  }

  agentFlow.classList.remove("is-working");
  agentFlow.classList.toggle("is-done", Boolean(isSuccess));

  if (isSuccess) {
    if (stageMs) {
      setAgentMetrics("Pipeline selesai. Semua agent telah mengeksekusi tahapan dengan sukses.");
      replayStagesFromMetrics(stageMs);
    } else {
      setAgentStage(4, "Selesai • Playlist siap diputar");
      setRuntimeVisualState("done");
      setAgentMetrics("Pipeline selesai. Playlist siap diputar.");
    }
  } else {
    setAgentStage(0, "Terhenti • Coba lagi");
    setRuntimeVisualState("error");
    setAgentMetrics("Milestone backend tidak tersedia karena request gagal.");
  }
}

function startAgentAnimation() {
  if (agentStageTimer) {
    clearInterval(agentStageTimer);
  }

  const stages = [
    [1, "Profiler Agent • Memahami mood dan aktivitas"],
    [2, "Spotify Search Agent • Menelusuri kandidat lagu"],
    [3, "Filter & Ranker Agent • Menilai relevansi"],
    [4, "Presenter Agent • Menyusun hasil terbaik"],
  ];

  let idx = 0;
  agentFlow.classList.remove("is-done");
  agentFlow.classList.add("is-working");
  setAgentMetrics("Merekam progres backend...");
  setAgentStage(stages[idx][0], stages[idx][1]);

  agentStageTimer = setInterval(() => {
    idx = (idx + 1) % stages.length;
    setAgentStage(stages[idx][0], stages[idx][1]);
  }, 900);
}

function renderSummary(data) {
  const profile = data.intent_profile || {};
  const quality = data.quality_notes || {};

  summaryMood.textContent = profile.mood || "-";
  summaryActivity.textContent = profile.activity || "-";
  summaryCount.textContent = String(data.summary?.returned_count ?? 0);

  const profilerMode = quality.llm_profiler_used ? "LLM" : "Heuristic";
  const rankerMode = quality.llm_ranker_used ? "LLM" : "Heuristic";
  summaryMode.textContent = `${profilerMode}/${rankerMode}`;
}

function renderRecommendations(data) {
  recommendationList.innerHTML = "";
  if (currentPreviewAudio) {
    currentPreviewAudio.pause();
    currentPreviewAudio = null;
  }
  if (currentPreviewButton) {
    currentPreviewButton.setAttribute("aria-pressed", "false");
    currentPreviewButton.textContent = "Play Preview";
    currentPreviewButton = null;
  }
  const list = data.recommendations || [];

  if (!list.length) {
    recommendationList.innerHTML = "<p class=\"empty-state\">Belum ada rekomendasi. Coba ubah deskripsi mood kamu.</p>";
    resultLead.textContent = "Belum ada hasil yang cocok. Ubah deskripsi mood atau aktivitas untuk hasil yang lebih pas.";
    return;
  }

  resultLead.textContent = `${list.length} lagu dipilih untuk kamu. Klik alasan jika ingin melihat detail lebih banyak.`;

  list.forEach((item, index) => {
    const card = document.createElement("article");
    card.className = "track-card magic-card enter";
    card.style.setProperty("--stagger-index", String(index));

    const top = document.createElement("div");
    top.className = "track-top";

    const rank = document.createElement("p");
    rank.className = "track-rank";
    rank.textContent = `#${item.rank}`;

    const score = document.createElement("p");
    score.className = "track-score";
    score.textContent = `match ${Math.round(Number(item.score || 0) * 100)}%`;

    top.appendChild(rank);
    top.appendChild(score);

    const title = document.createElement("p");
    title.className = "track-title";
    title.textContent = item.title;

    const meta = document.createElement("p");
    meta.className = "track-meta";
    meta.textContent = `${item.artist} | score: ${Number(item.score).toFixed(4)}`;

    const why = document.createElement("p");
    why.className = "track-why";
    why.textContent = item.why || "Alasan belum tersedia.";

    const isLongReason = why.textContent.length > 110;
    if (isLongReason) {
      why.classList.add("collapsed");
    }

    const actions = document.createElement("div");
    actions.className = "track-actions";

    if (item.preview_url) {
      const previewBtn = document.createElement("button");
      previewBtn.type = "button";
      previewBtn.className = "preview-btn";
      previewBtn.setAttribute("aria-pressed", "false");
      previewBtn.textContent = "Play Preview";

      previewBtn.addEventListener("click", () => {
        const isCurrent = currentPreviewButton === previewBtn;

        if (isCurrent && currentPreviewAudio && !currentPreviewAudio.paused) {
          currentPreviewAudio.pause();
          previewBtn.setAttribute("aria-pressed", "false");
          previewBtn.textContent = "Play Preview";
          return;
        }

        if (currentPreviewAudio) {
          currentPreviewAudio.pause();
        }
        if (currentPreviewButton) {
          currentPreviewButton.setAttribute("aria-pressed", "false");
          currentPreviewButton.textContent = "Play Preview";
        }

        const audio = new Audio(item.preview_url);
        audio.volume = 0.95;

        audio.addEventListener("ended", () => {
          previewBtn.setAttribute("aria-pressed", "false");
          previewBtn.textContent = "Play Preview";
          if (currentPreviewButton === previewBtn) {
            currentPreviewButton = null;
            currentPreviewAudio = null;
          }
        });

        audio.addEventListener("pause", () => {
          if (audio.ended) return;
          previewBtn.setAttribute("aria-pressed", "false");
          previewBtn.textContent = "Play Preview";
        });

        audio
          .play()
          .then(() => {
            currentPreviewAudio = audio;
            currentPreviewButton = previewBtn;
            previewBtn.setAttribute("aria-pressed", "true");
            previewBtn.textContent = "Pause Preview";
          })
          .catch(() => {
            setStatus("Preview tidak bisa diputar di browser ini atau diblokir autoplay.", true);
            previewBtn.setAttribute("aria-pressed", "false");
            previewBtn.textContent = "Play Preview";
          });
      });

      actions.appendChild(previewBtn);
    }

    if (isLongReason) {
      const toggleWhy = document.createElement("button");
      toggleWhy.className = "text-btn";
      toggleWhy.type = "button";
      toggleWhy.textContent = "Lihat alasan";
      toggleWhy.addEventListener("click", () => {
        const collapsed = why.classList.toggle("collapsed");
        toggleWhy.textContent = collapsed ? "Lihat alasan" : "Sembunyikan";
      });
      actions.appendChild(toggleWhy);
    }

    card.appendChild(top);
    card.appendChild(title);
    card.appendChild(meta);
    card.appendChild(why);

    if (item.spotify_url) {
      const link = document.createElement("a");
      link.className = "track-link";
      link.href = item.spotify_url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = "Buka di Spotify";
      actions.appendChild(link);
    }

    if (actions.childElementCount > 0) {
      card.appendChild(actions);
    }

    recommendationList.appendChild(card);
  });

  if (list.length > 0) {
    const exportContainer = document.createElement("div");
    exportContainer.style.setProperty("grid-column", "1 / -1");
    exportContainer.style.marginTop = "24px";
    exportContainer.style.display = "flex";
    exportContainer.style.justifyContent = "center";

    const exportBtn = document.createElement("button");
    exportBtn.className = "shimmer-btn";
    exportBtn.style.width = "100%";
    exportBtn.style.maxWidth = "400px";
    exportBtn.style.marginTop = "16px";

    exportBtn.onmouseover = () => { exportBtn.style.transform = "scale(1.05)"; };
    exportBtn.onmouseout = () => { exportBtn.style.transform = "scale(1)"; };

    const hasToken = !!localStorage.getItem("spotify_token");
    exportBtn.textContent = hasToken ? "Save as Spotify Playlist" : "Login to Save to Spotify";

    exportBtn.addEventListener("click", async () => {
      if (!hasToken) {
        window.location.href = "/auth/login";
        return;
      }
      
      exportBtn.disabled = true;
      exportBtn.textContent = "Creating Playlist...";
      exportBtn.style.opacity = "0.7";
      
      try {
        const trackIds = list
          .filter((i) => i.spotify_url && i.spotify_url.includes("/track/"))
          .map((i) => i.spotify_url.split("/track/")[1].split("?")[0]);
          
        const payload = {
          user_token: localStorage.getItem("spotify_token"),
          title: `SmartDiscover: ${data.intent_profile?.mood || "Playlist"}`,
          description: `Rekomendasi playlist otomatis untuk aktivitas: ${data.intent_profile?.activity || "Personal"}`,
          track_ids: trackIds,
        };
        
        const res = await fetch("/create-playlist", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        let resData = {};
        const contentType = res.headers.get("content-type") || "";
        if (contentType.includes("application/json")) {
          resData = await res.json();
        } else {
          const rawText = await res.text();
          resData = { error: rawText || "Unknown server error" };
        }

        if (!res.ok) {
          if (res.status === 401) {
            localStorage.removeItem("spotify_token");
            if (spotifyLoginBtn) {
              spotifyLoginBtn.textContent = "Connect Spotify";
              spotifyLoginBtn.style.backgroundColor = "transparent";
              spotifyLoginBtn.style.border = "1px solid rgba(255,255,255,0.2)";
              spotifyLoginBtn.style.color = "#ccc";
              spotifyLoginBtn.disabled = false;
            }
            throw new Error("Spotify session expired. Please connect Spotify again.");
          }

          throw new Error(
            resData.detail || resData.error || `Failed to create playlist (${res.status})`
          );
        }

        if (resData.url) {
          exportBtn.textContent = "Playlist Created! (Click to Open)";
          exportBtn.style.opacity = "1";
          exportBtn.onclick = () => window.open(resData.url, "_blank");
          exportBtn.disabled = false;
          setStatus("Berhasil! Playlist telah disimpan ke akun Spotify kamu.", false);
        } else {
          throw new Error(resData.error || "Gagal membuat playlist");
        }
      } catch (err) {
        exportBtn.textContent = "Error. Try Again";
        exportBtn.disabled = false;
        exportBtn.style.opacity = "1";
        exportBtn.style.backgroundColor = "#ff8f8f"; // error red
        setStatus(`Gagal export playlist: ${err.message}`, true);
      }
    });

    exportContainer.appendChild(exportBtn);
    recommendationList.appendChild(exportContainer);
  }
}

function renderLoadingSkeleton(targetCount) {
  if (currentPreviewAudio) {
    currentPreviewAudio.pause();
    currentPreviewAudio = null;
  }
  if (currentPreviewButton) {
    currentPreviewButton.setAttribute("aria-pressed", "false");
    currentPreviewButton.textContent = "Play Preview";
    currentPreviewButton = null;
  }
  const count = Math.max(4, Math.min(Number(targetCount) || 6, 8));
  recommendationList.innerHTML = "";
  resultLead.textContent = "Sedang menyiapkan daftar lagu paling cocok...";

  for (let i = 0; i < count; i += 1) {
    const card = document.createElement("article");
    card.className = "skeleton-card";

    const line1 = document.createElement("div");
    line1.className = "skeleton-line short";

    const line2 = document.createElement("div");
    line2.className = "skeleton-line";

    const line3 = document.createElement("div");
    line3.className = "skeleton-line medium";

    card.appendChild(line1);
    card.appendChild(line2);
    card.appendChild(line3);
    recommendationList.appendChild(card);
  }
}

async function requestRecommendations(event) {
  event.preventDefault();
  const text = intentInput.value.trim();
  const targetCount = Number(targetCountInput.value || 15);

  if (!text) {
    setStatus("Intent wajib diisi.", true);
    return;
  }

  submitBtn.disabled = true;
  setStatus("Mencari rekomendasi terbaik untuk kamu...");
  startAgentAnimation();
  renderLoadingSkeleton(targetCount);

  try {
    const response = await fetch("/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, target_count: targetCount }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Request failed (${response.status}): ${errorText}`);
    }

    const data = await response.json();
    renderSummary(data);
    renderRecommendations(data);

    const quality = data.quality_notes || {};
    const profilerMode = quality.llm_profiler_used ? "LLM" : "heuristic";
    const rankerMode = quality.llm_ranker_used ? "LLM" : "heuristic";

    setStatus(
      `${data.summary.returned_count} lagu ditemukan. Profiler=${profilerMode}, Ranker=${rankerMode}.`
    );
    stopAgentAnimation(true, data.quality_notes?.stage_ms || null);
  } catch (error) {
    setStatus(error.message || "Terjadi error saat memanggil API.", true);
    recommendationList.innerHTML = "<p class=\"empty-state\">Gagal memuat rekomendasi. Coba lagi sebentar.</p>";
    resultLead.textContent = "Terjadi kendala saat mengambil rekomendasi.";
    stopAgentAnimation(false);
  } finally {
    submitBtn.disabled = false;
  }
}

async function checkLlmHealth(showStatusMessage = false) {
  setLlmBadge("LLM: checking...", "neutral");

  try {
    const response = await fetch("/llm/health");
    if (!response.ok) {
      throw new Error(`LLM health failed (${response.status})`);
    }
    const data = await response.json();
    const model = data.model || "unknown-model";

    if (data.ok) {
      setLlmBadge(`LLM: online (${model})`, "ok");
      if (showStatusMessage) {
        setStatus(`LLM ready on model ${model}.`);
      }
      return;
    }

    const isDisabled = data.status === "disabled";
    setLlmBadge(
      isDisabled ? "LLM: disabled (fallback active)" : "LLM: degraded",
      isDisabled ? "warn" : "error"
    );

    if (showStatusMessage) {
      setStatus(`LLM status: ${data.status}. ${data.details || ""}`.trim(), !isDisabled);
    }
  } catch (error) {
    setLlmBadge("LLM: unreachable", "error");
    if (showStatusMessage) {
      setStatus(error.message || "Gagal cek LLM health.", true);
    }
  }
}

async function checkSpotifyHealth() {
  healthBtn.disabled = true;
  setStatus("Checking Spotify health...");

  try {
    const response = await fetch("/spotify/health");
    if (!response.ok) {
      throw new Error(`Spotify health failed (${response.status})`);
    }
    const data = await response.json();
    const detail = data.details ? ` ${data.details}` : "";
    if (data.ok) {
      setSpotifyBadge("Spotify: online", "ok");
    } else if (data.status === "mock-mode") {
      setSpotifyBadge("Spotify: mock mode", "warn");
    } else {
      setSpotifyBadge("Spotify: degraded", "error");
    }
    setStatus(`Spotify: ${data.status}.${detail}`);
  } catch (error) {
    setSpotifyBadge("Spotify: unreachable", "error");
    setStatus(error.message || "Gagal cek Spotify health.", true);
  } finally {
    healthBtn.disabled = false;
  }
}

function bindQuickPrompts() {
  quickPrompts.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLButtonElement)) {
      return;
    }
    const intent = target.dataset.intent;
    if (!intent) {
      return;
    }
    intentInput.value = intent;
    intentInput.focus();
    setStatus("Contoh intent terisi. Kamu bisa langsung cari rekomendasi.");
  });
}

function handleOAuthToken() {
  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get("token");
  if (token) {
    localStorage.setItem("spotify_token", token);
    window.history.replaceState({}, document.title, window.location.pathname);
    setStatus("Berhasil login! Akun Spotify siap digunakan untuk menyimpan playlist.");
  }
  
  if (localStorage.getItem("spotify_token") && spotifyLoginBtn) {
    spotifyLoginBtn.textContent = "Spotify Connected ✓";
    spotifyLoginBtn.style.backgroundColor = "transparent";
    spotifyLoginBtn.style.border = "1px solid #1DB954";
    spotifyLoginBtn.style.color = "#1DB954";
    spotifyLoginBtn.disabled = true;
  }
}

if (spotifyLoginBtn) {
  spotifyLoginBtn.addEventListener("click", () => {
    window.location.href = "/auth/login";
  });
}

form.addEventListener("submit", requestRecommendations);
healthBtn.addEventListener("click", checkSpotifyHealth);
bindQuickPrompts();
bindRuntimePreferences();
bindPipelineGeometrySync();
startRuntimeFrameLoop();
checkLlmHealth();
checkSpotifyHealth();
handleOAuthToken();
setAgentStage(0, "Idle • Menunggu perintah");
setAgentMetrics("Milestone backend akan tampil setelah request selesai.");
