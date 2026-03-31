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
const resultsPanel = document.querySelector(".results-panel");
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
const langIdBtn = document.getElementById("langIdBtn");
const langEnBtn = document.getElementById("langEnBtn");
const langSwitch = document.getElementById("langSwitch");
const trackDetailModal = document.getElementById("trackDetailModal");
const trackDetailOverlay = document.getElementById("trackDetailOverlay");
const trackDetailCloseBtn = document.getElementById("trackDetailCloseBtn");
const trackDetailTitle = document.getElementById("trackDetailTitle");
const trackDetailSong = document.getElementById("trackDetailSong");
const trackDetailArtist = document.getElementById("trackDetailArtist");
const trackDetailScoreLabel = document.getElementById("trackDetailScoreLabel");
const trackDetailScoreValue = document.getElementById("trackDetailScoreValue");
const trackDetailPreviewLabel = document.getElementById("trackDetailPreviewLabel");
const trackDetailPreviewValue = document.getElementById("trackDetailPreviewValue");
const trackDetailReasonLabel = document.getElementById("trackDetailReasonLabel");
const trackDetailReasonText = document.getElementById("trackDetailReasonText");
const trackDetailSpotifyLink = document.getElementById("trackDetailSpotifyLink");

const subtitleText = document.getElementById("subtitleText");
const intentLabel = document.getElementById("intentLabel");
const targetCountLabel = document.getElementById("targetCountLabel");
const submitText = document.getElementById("submitText");
const quickPromptLabel = document.getElementById("quickPromptLabel");
const chipFocus = document.getElementById("chipFocus");
const chipRain = document.getElementById("chipRain");
const chipWorkout = document.getElementById("chipWorkout");
const insightEngineLabel = document.getElementById("insightEngineLabel");
const insightEngineValue = document.getElementById("insightEngineValue");
const insightLatencyLabel = document.getElementById("insightLatencyLabel");
const insightLatencyValue = document.getElementById("insightLatencyValue");
const insightOutputLabel = document.getElementById("insightOutputLabel");
const insightOutputValue = document.getElementById("insightOutputValue");
const pipelineTitle = document.getElementById("pipelineTitle");
const statMoodLabel = document.getElementById("statMoodLabel");
const statActivityLabel = document.getElementById("statActivityLabel");
const statCountLabel = document.getElementById("statCountLabel");
const statModeLabel = document.getElementById("statModeLabel");
const resultsTitle = document.getElementById("resultsTitle");
const resultsPill = document.getElementById("resultsPill");

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
let currentPreviewCard = null;
let currentPreviewProgressFill = null;
let currentPreviewElapsed = null;
let currentPreviewDuration = null;
let currentPreviewMeter = null;
let currentPreviewRaf = 0;
let lastRenderedData = null;
let lastRenderedSourceText = "";
let currentDetailItem = null;

const LANG_STORAGE_KEY = "smartdiscover_lang";
const supportedLangs = new Set(["id", "en"]);
let currentLang = localStorage.getItem(LANG_STORAGE_KEY) || "id";
if (!supportedLangs.has(currentLang)) {
  currentLang = "id";
}

const I18N = {
  id: {
    subtitle: "AI-Driven Spotify Curation in a single prompt.",
    intentLabel: "Apa mood atau aktivitasmu?",
    intentPlaceholder: "contoh: lagu sedih pas nge-bug jam 2 pagi...",
    targetCountLabel: "Berapa Lagu?",
    submit: "Mulai Kurasi",
    quickPromptLabel: "Coba Prompt Bebas:",
    chipFocus: "Fokus Kerja",
    chipRain: "Hujan Malam",
    chipWorkout: "Workout",
    connectSpotify: "Connect Spotify",
    checkHealth: "Check Health",
    insightEngineLabel: "Engine",
    insightEngineValue: "Multi-Agent Music Graph",
    insightLatencyLabel: "Latency",
    insightLatencyValue: "Adaptive Fast Path",
    insightOutputLabel: "Output",
    insightOutputValue: "Ready-to-Play Picks",
    pipelineTitle: "Agent Neural Pipeline",
    stageIdle: "Idle • Menunggu perintah",
    stageProfiler: "Profiler Agent • Memahami mood dan aktivitas",
    stageSearch: "Spotify Search Agent • Menelusuri kandidat lagu",
    stageRanker: "Filter & Ranker Agent • Menilai relevansi",
    stagePresenter: "Presenter Agent • Menyusun hasil terbaik",
    stageDone: "Selesai • Playlist siap diputar",
    stageStopped: "Terhenti • Coba lagi",
    metricsDefault: "Milestone backend akan tampil setelah request selesai.",
    metricsWorking: "Merekam progres backend...",
    metricsDone: "Pipeline selesai. Semua agent telah mengeksekusi tahapan dengan sukses.",
    metricsDoneSimple: "Pipeline selesai. Playlist siap diputar.",
    metricsError: "Milestone backend tidak tersedia karena request gagal.",
    statMood: "Mood Terdeteksi",
    statActivity: "Aktivitas",
    statCount: "Jumlah Track",
    statMode: "Engine Mode",
    resultsTitle: "Rekomendasi Terbaik",
    resultsPill: "Smart Match Feed",
    resultLeadInitial: "Masukan prompt di panel kiri untuk memulai iterasi.",
    resultLeadNoResult: "Belum ada hasil yang cocok. Ubah deskripsi mood atau aktivitas untuk hasil yang lebih pas.",
    emptyNoRecommendation: "Belum ada rekomendasi. Coba ubah deskripsi mood kamu.",
    resultLeadFound: "{count} lagu dipilih untuk kamu. Klik alasan jika ingin melihat detail lebih banyak.",
    matchLabel: "match",
    scoreLabel: "score",
    whyFallback: "Alasan belum tersedia.",
    previewPlay: "Play",
    previewPause: "Pause",
    previewNoPreview: "No Preview",
    previewUnavailable: "preview unavailable",
    previewLabel: "preview",
    previewAriaPlay: "Play preview 30 detik",
    previewAriaPause: "Pause preview",
    previewAriaUnavailable: "Preview tidak tersedia untuk track ini",
    previewAriaMeter: "Progress preview lagu",
    previewAutoplayError: "Preview tidak bisa diputar di browser ini atau diblokir autoplay.",
    seeReason: "Lihat alasan",
    hideReason: "Sembunyikan",
    detailButton: "Detail",
    detailTitle: "Detail Lagu",
    detailScore: "Score",
    detailPreview: "Preview",
    detailReason: "Alasan",
    detailPreviewAvailable: "Tersedia",
    detailPreviewUnavailable: "Tidak tersedia",
    detailCloseAria: "Tutup",
    openSpotify: "Buka di Spotify",
    exportSave: "Save as Spotify Playlist",
    exportLogin: "Login to create playlist on spotify",
    exportCreating: "Creating Playlist...",
    exportCreated: "Playlist Created! (Click to Open)",
    exportErrorTryAgain: "Error. Try Again",
    exportSuccessStatus: "Berhasil! Playlist telah disimpan ke akun Spotify kamu.",
    exportFailed: "Gagal export playlist: {error}",
    spotifyExpired: "Spotify session expired. Please connect Spotify again.",
    genericFailedPlaylist: "Gagal membuat playlist",
    loadingLead: "Sedang menyiapkan daftar lagu paling cocok...",
    intentRequired: "Intent wajib diisi.",
    searching: "Mencari rekomendasi terbaik untuk kamu...",
    foundStatus: "{count} lagu ditemukan. Profiler={profilerMode}, Ranker={rankerMode}.",
    requestErrorDefault: "Terjadi error saat memanggil API.",
    loadError: "Gagal memuat rekomendasi. Coba lagi sebentar.",
    loadErrorLead: "Terjadi kendala saat mengambil rekomendasi.",
    llmChecking: "LLM: checking...",
    llmOnline: "LLM: online ({model})",
    llmReadyStatus: "LLM ready on model {model}.",
    llmDisabled: "LLM: disabled (fallback active)",
    llmDegraded: "LLM: degraded",
    llmStatus: "LLM status: {status}. {details}",
    llmUnreachable: "LLM: unreachable",
    llmHealthError: "Gagal cek LLM health.",
    spotifyCheckingStatus: "Checking Spotify health...",
    spotifyOnline: "Spotify: online",
    spotifyMock: "Spotify: mock mode",
    spotifyDegraded: "Spotify: degraded",
    spotifyStatus: "Spotify: {status}.{detail}",
    spotifyUnreachable: "Spotify: unreachable",
    spotifyHealthError: "Gagal cek Spotify health.",
    promptFilled: "Contoh intent terisi. Kamu bisa langsung cari rekomendasi.",
    oauthSuccess: "Berhasil login! Akun Spotify siap digunakan untuk menyimpan playlist.",
    spotifyConnected: "Spotify Connected ✓",
  },
  en: {
    subtitle: "AI-Driven Spotify curation in a single prompt.",
    intentLabel: "What is your mood or activity?",
    intentPlaceholder: "example: sad songs while fixing bugs at 2 AM...",
    targetCountLabel: "How Many Songs?",
    submit: "Start Curation",
    quickPromptLabel: "Try Quick Prompts:",
    chipFocus: "Work Focus",
    chipRain: "Rainy Night",
    chipWorkout: "Workout",
    connectSpotify: "Connect Spotify",
    checkHealth: "Check Health",
    insightEngineLabel: "Engine",
    insightEngineValue: "Multi-Agent Music Graph",
    insightLatencyLabel: "Latency",
    insightLatencyValue: "Adaptive Fast Path",
    insightOutputLabel: "Output",
    insightOutputValue: "Ready-to-Play Picks",
    pipelineTitle: "Agent Neural Pipeline",
    stageIdle: "Idle • Waiting for command",
    stageProfiler: "Profiler Agent • Understanding mood and activity",
    stageSearch: "Spotify Search Agent • Retrieving candidate tracks",
    stageRanker: "Filter & Ranker Agent • Evaluating relevance",
    stagePresenter: "Presenter Agent • Assembling best results",
    stageDone: "Done • Playlist ready to play",
    stageStopped: "Stopped • Please try again",
    metricsDefault: "Backend milestones will appear after a request finishes.",
    metricsWorking: "Capturing backend progress...",
    metricsDone: "Pipeline finished. All agents executed successfully.",
    metricsDoneSimple: "Pipeline finished. Playlist is ready.",
    metricsError: "Backend milestones are unavailable because the request failed.",
    statMood: "Detected Mood",
    statActivity: "Activity",
    statCount: "Track Count",
    statMode: "Engine Mode",
    resultsTitle: "Top Recommendations",
    resultsPill: "Smart Match Feed",
    resultLeadInitial: "Enter a prompt on the left panel to start the pipeline.",
    resultLeadNoResult: "No matching results yet. Adjust your mood or activity description for better recommendations.",
    emptyNoRecommendation: "No recommendations yet. Try refining your mood description.",
    resultLeadFound: "{count} songs were selected for you. Click reason to see more details.",
    matchLabel: "match",
    scoreLabel: "score",
    whyFallback: "Reason is not available yet.",
    previewPlay: "Play",
    previewPause: "Pause",
    previewNoPreview: "No Preview",
    previewUnavailable: "preview unavailable",
    previewLabel: "preview",
    previewAriaPlay: "Play 30-second preview",
    previewAriaPause: "Pause preview",
    previewAriaUnavailable: "Preview is unavailable for this track",
    previewAriaMeter: "Track preview progress",
    previewAutoplayError: "Preview cannot be played in this browser or autoplay is blocked.",
    seeReason: "See reason",
    hideReason: "Hide",
    detailButton: "Details",
    detailTitle: "Track Details",
    detailScore: "Score",
    detailPreview: "Preview",
    detailReason: "Reason",
    detailPreviewAvailable: "Available",
    detailPreviewUnavailable: "Unavailable",
    detailCloseAria: "Close",
    openSpotify: "Open in Spotify",
    exportSave: "Save as Spotify Playlist",
    exportLogin: "Login to create playlist on spotify",
    exportCreating: "Creating Playlist...",
    exportCreated: "Playlist Created! (Click to Open)",
    exportErrorTryAgain: "Error. Try Again",
    exportSuccessStatus: "Success! Playlist has been saved to your Spotify account.",
    exportFailed: "Failed to export playlist: {error}",
    spotifyExpired: "Spotify session expired. Please connect Spotify again.",
    genericFailedPlaylist: "Failed to create playlist",
    loadingLead: "Preparing the most relevant song list...",
    intentRequired: "Intent is required.",
    searching: "Finding the best recommendations for you...",
    foundStatus: "{count} songs found. Profiler={profilerMode}, Ranker={rankerMode}.",
    requestErrorDefault: "An error occurred while calling the API.",
    loadError: "Failed to load recommendations. Please try again shortly.",
    loadErrorLead: "There was a problem while fetching recommendations.",
    llmChecking: "LLM: checking...",
    llmOnline: "LLM: online ({model})",
    llmReadyStatus: "LLM is ready on model {model}.",
    llmDisabled: "LLM: disabled (fallback active)",
    llmDegraded: "LLM: degraded",
    llmStatus: "LLM status: {status}. {details}",
    llmUnreachable: "LLM: unreachable",
    llmHealthError: "Failed to check LLM health.",
    spotifyCheckingStatus: "Checking Spotify health...",
    spotifyOnline: "Spotify: online",
    spotifyMock: "Spotify: mock mode",
    spotifyDegraded: "Spotify: degraded",
    spotifyStatus: "Spotify: {status}.{detail}",
    spotifyUnreachable: "Spotify: unreachable",
    spotifyHealthError: "Failed to check Spotify health.",
    promptFilled: "Sample intent applied. You can run recommendations now.",
    oauthSuccess: "Login successful! Spotify is ready for playlist export.",
    spotifyConnected: "Spotify Connected ✓",
  },
};

function tr(key, vars = {}) {
  const table = I18N[currentLang] || I18N.id;
  const fallback = I18N.id[key] || key;
  const template = table[key] || fallback;
  return String(template).replace(/\{(\w+)\}/g, (_, name) => {
    const value = vars[name];
    return value === undefined || value === null ? "" : String(value);
  });
}

function applyLanguageUI() {
  document.documentElement.lang = currentLang;
  if (subtitleText) subtitleText.textContent = tr("subtitle");
  if (intentLabel) intentLabel.textContent = tr("intentLabel");
  if (intentInput) intentInput.setAttribute("placeholder", tr("intentPlaceholder"));
  if (targetCountLabel) targetCountLabel.textContent = tr("targetCountLabel");
  if (submitText) submitText.textContent = tr("submit");
  if (quickPromptLabel) quickPromptLabel.textContent = tr("quickPromptLabel");
  if (chipFocus) chipFocus.textContent = tr("chipFocus");
  if (chipRain) chipRain.textContent = tr("chipRain");
  if (chipWorkout) chipWorkout.textContent = tr("chipWorkout");
  if (healthBtn) healthBtn.textContent = tr("checkHealth");
  if (insightEngineLabel) insightEngineLabel.textContent = tr("insightEngineLabel");
  if (insightEngineValue) insightEngineValue.textContent = tr("insightEngineValue");
  if (insightLatencyLabel) insightLatencyLabel.textContent = tr("insightLatencyLabel");
  if (insightLatencyValue) insightLatencyValue.textContent = tr("insightLatencyValue");
  if (insightOutputLabel) insightOutputLabel.textContent = tr("insightOutputLabel");
  if (insightOutputValue) insightOutputValue.textContent = tr("insightOutputValue");
  if (pipelineTitle) pipelineTitle.textContent = tr("pipelineTitle");
  if (statMoodLabel) statMoodLabel.textContent = tr("statMood");
  if (statActivityLabel) statActivityLabel.textContent = tr("statActivity");
  if (statCountLabel) statCountLabel.textContent = tr("statCount");
  if (statModeLabel) statModeLabel.textContent = tr("statMode");
  if (resultsTitle) resultsTitle.textContent = tr("resultsTitle");
  if (resultsPill) resultsPill.textContent = tr("resultsPill");
  if (!recommendationList?.childElementCount && resultLead) {
    resultLead.textContent = tr("resultLeadInitial");
  }

  if (spotifyLoginBtn && !localStorage.getItem("spotify_token")) {
    spotifyLoginBtn.textContent = tr("connectSpotify");
  }

  if (trackDetailTitle) trackDetailTitle.textContent = tr("detailTitle");
  if (trackDetailScoreLabel) trackDetailScoreLabel.textContent = tr("detailScore");
  if (trackDetailPreviewLabel) trackDetailPreviewLabel.textContent = tr("detailPreview");
  if (trackDetailReasonLabel) trackDetailReasonLabel.textContent = tr("detailReason");
  if (trackDetailCloseBtn) trackDetailCloseBtn.setAttribute("aria-label", tr("detailCloseAria"));
  if (trackDetailOverlay) trackDetailOverlay.setAttribute("aria-label", tr("detailCloseAria"));

  if (langIdBtn && langEnBtn) {
    const isId = currentLang === "id";
    langIdBtn.classList.toggle("is-active", isId);
    langEnBtn.classList.toggle("is-active", !isId);
    langIdBtn.setAttribute("aria-pressed", String(isId));
    langEnBtn.setAttribute("aria-pressed", String(!isId));
  }
}

function setLanguage(lang) {
  if (!supportedLangs.has(lang)) return;
  currentLang = lang;
  localStorage.setItem(LANG_STORAGE_KEY, lang);
  applyLanguageUI();
  setAgentStage(Number(agentFlow?.dataset?.stage || 0), getStageText(Number(agentFlow?.dataset?.stage || 0)));
  if (lastRenderedData) {
    renderRecommendations(lastRenderedData, lastRenderedSourceText);
  }
  if (currentDetailItem) {
    renderTrackDetailContent(currentDetailItem);
  }
}

function renderTrackDetailContent(item) {
  if (!item) return;
  currentDetailItem = item;
  if (trackDetailSong) trackDetailSong.textContent = item.title || "-";
  if (trackDetailArtist) trackDetailArtist.textContent = item.artist || "-";
  if (trackDetailScoreValue) trackDetailScoreValue.textContent = `${Math.round(Number(item.score || 0) * 100)}%`;
  if (trackDetailPreviewValue) trackDetailPreviewValue.textContent = item.preview_url ? tr("detailPreviewAvailable") : tr("detailPreviewUnavailable");
  if (trackDetailReasonText) trackDetailReasonText.textContent = item.why || tr("whyFallback");
  if (trackDetailSpotifyLink) {
    trackDetailSpotifyLink.textContent = tr("openSpotify");
    if (item.spotify_url) {
      trackDetailSpotifyLink.href = item.spotify_url;
      trackDetailSpotifyLink.style.display = "inline-flex";
    } else {
      trackDetailSpotifyLink.href = "#";
      trackDetailSpotifyLink.style.display = "none";
    }
  }
}

function openTrackDetailModal(item) {
  if (!trackDetailModal || !item) return;
  renderTrackDetailContent(item);
  trackDetailModal.classList.add("is-open");
  trackDetailModal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
}

function closeTrackDetailModal() {
  if (!trackDetailModal) return;
  trackDetailModal.classList.remove("is-open");
  trackDetailModal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
}

function bindTrackDetailModal() {
  if (trackDetailOverlay) {
    trackDetailOverlay.addEventListener("click", closeTrackDetailModal);
  }
  if (trackDetailCloseBtn) {
    trackDetailCloseBtn.addEventListener("click", closeTrackDetailModal);
  }
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeTrackDetailModal();
    }
  });
}

function bindLanguageSwitch() {
  if (langSwitch) {
    langSwitch.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      const button = target.closest(".lang-btn");
      if (!(button instanceof HTMLButtonElement)) return;
      if (button.id === "langIdBtn") {
        setLanguage("id");
      } else if (button.id === "langEnBtn") {
        setLanguage("en");
      }
    });
    return;
  }

  if (langIdBtn) {
    langIdBtn.addEventListener("click", () => setLanguage("id"));
  }
  if (langEnBtn) {
    langEnBtn.addEventListener("click", () => setLanguage("en"));
  }
}

function getStageText(stage) {
  if (stage === 1) return tr("stageProfiler");
  if (stage === 2) return tr("stageSearch");
  if (stage === 3) return tr("stageRanker");
  if (stage === 4) return tr("stagePresenter");
  return tr("stageIdle");
}

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

function toTitleCaseToken(value) {
  if (!value || typeof value !== "string") return "";
  return value
    .replace(/[_-]+/g, " ")
    .trim()
    .split(/\s+/)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function buildPlaylistTitle(data, sourceText) {
  const profile = data?.intent_profile || {};
  const activity = profile.activity && profile.activity !== "listening"
    ? toTitleCaseToken(profile.activity)
    : "";
  const genre = Array.isArray(profile.genre) && profile.genre.length
    ? toTitleCaseToken(String(profile.genre[0]))
    : "";
  const promptFallback = String(sourceText || "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 24);

  const core = activity || genre || promptFallback || "Personal Mix";
  const dateText = new Date().toISOString().slice(0, 10);
  return `SmartDiscover - ${core} - ${dateText}`;
}

function buildPlaylistDescription(data, sourceText) {
  const profile = data?.intent_profile || {};
  const activity = toTitleCaseToken(profile.activity || "Listening");
  const mood = toTitleCaseToken(profile.mood || "Neutral");
  const promptCompact = String(sourceText || "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 80);

  if (promptCompact) {
    return `SmartDiscover auto playlist for ${activity} (${mood}). Prompt: ${promptCompact}`;
  }
  return `SmartDiscover auto playlist for ${activity} (${mood}).`;
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

function formatPreviewTime(seconds) {
  const safeSeconds = Number.isFinite(seconds) && seconds > 0 ? seconds : 0;
  const mins = Math.floor(safeSeconds / 60);
  const secs = Math.floor(safeSeconds % 60);
  return `${mins}:${String(secs).padStart(2, "0")}`;
}

function stopPreviewProgressLoop() {
  if (currentPreviewRaf) {
    cancelAnimationFrame(currentPreviewRaf);
    currentPreviewRaf = 0;
  }
}

function updatePreviewProgressUI() {
  if (!currentPreviewAudio || !currentPreviewProgressFill || !currentPreviewElapsed) {
    stopPreviewProgressLoop();
    return;
  }

  const duration = Number.isFinite(currentPreviewAudio.duration) && currentPreviewAudio.duration > 0
    ? currentPreviewAudio.duration
    : 30;
  const currentTime = Math.max(0, currentPreviewAudio.currentTime || 0);
  const progressPct = Math.min(100, (currentTime / duration) * 100);

  currentPreviewProgressFill.style.width = `${progressPct}%`;
  if (currentPreviewMeter) {
    currentPreviewMeter.setAttribute("aria-valuenow", String(Math.round(progressPct)));
  }
  currentPreviewElapsed.textContent = formatPreviewTime(currentTime);
  if (currentPreviewDuration) {
    currentPreviewDuration.textContent = `${formatPreviewTime(duration)} ${tr("previewLabel")}`;
  }

  if (!currentPreviewAudio.paused && !currentPreviewAudio.ended) {
    currentPreviewRaf = requestAnimationFrame(updatePreviewProgressUI);
  } else {
    stopPreviewProgressLoop();
  }
}

function resetCurrentPreviewUI() {
  if (currentPreviewButton) {
    currentPreviewButton.setAttribute("aria-pressed", "false");
    currentPreviewButton.setAttribute("aria-label", tr("previewAriaPlay"));
    currentPreviewButton.textContent = tr("previewPlay");
  }
  if (currentPreviewCard) {
    currentPreviewCard.classList.remove("is-preview-playing");
  }
  if (currentPreviewProgressFill) {
    currentPreviewProgressFill.style.width = "0%";
  }
  if (currentPreviewMeter) {
    currentPreviewMeter.setAttribute("aria-valuenow", "0");
  }
  if (currentPreviewElapsed) {
    currentPreviewElapsed.textContent = "0:00";
  }
  stopPreviewProgressLoop();
}

function clearCurrentPreviewState() {
  if (currentPreviewAudio) {
    currentPreviewAudio.pause();
  }
  resetCurrentPreviewUI();
  currentPreviewAudio = null;
  currentPreviewButton = null;
  currentPreviewCard = null;
  currentPreviewProgressFill = null;
  currentPreviewElapsed = null;
  currentPreviewDuration = null;
  currentPreviewMeter = null;
}

async function replayStagesFromMetrics(stageMs) {
  const token = ++replayToken;
  const sequence = [
    [1, tr("stageProfiler"), Number(stageMs?.profiler || 0)],
    [2, tr("stageSearch"), Number(stageMs?.search || 0)],
    [3, tr("stageRanker"), Number(stageMs?.ranker || 0)],
    [4, tr("stagePresenter"), Number(stageMs?.presenter || 0)],
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
  setAgentStage(4, tr("stageDone"));
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
      setAgentMetrics(tr("metricsDone"));
      replayStagesFromMetrics(stageMs);
    } else {
      setAgentStage(4, tr("stageDone"));
      setRuntimeVisualState("done");
      setAgentMetrics(tr("metricsDoneSimple"));
    }
  } else {
    setAgentStage(0, tr("stageStopped"));
    setRuntimeVisualState("error");
    setAgentMetrics(tr("metricsError"));
  }
}

function startAgentAnimation() {
  if (agentStageTimer) {
    clearInterval(agentStageTimer);
  }

  const stages = [
    [1, tr("stageProfiler")],
    [2, tr("stageSearch")],
    [3, tr("stageRanker")],
    [4, tr("stagePresenter")],
  ];

  let idx = 0;
  agentFlow.classList.remove("is-done");
  agentFlow.classList.add("is-working");
  setAgentMetrics(tr("metricsWorking"));
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

function renderRecommendations(data, sourceText = "") {
  lastRenderedData = data;
  lastRenderedSourceText = sourceText;
  const existingExportBar = document.getElementById("exportActionBar");
  if (existingExportBar) {
    existingExportBar.remove();
  }
  recommendationList.innerHTML = "";
  clearCurrentPreviewState();
  const list = data.recommendations || [];

  if (!list.length) {
    recommendationList.innerHTML = `<p class=\"empty-state\">${tr("emptyNoRecommendation")}</p>`;
    resultLead.textContent = tr("resultLeadNoResult");
    return;
  }

  resultLead.textContent = tr("resultLeadFound", { count: list.length });

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
    score.textContent = `${tr("matchLabel")} ${Math.round(Number(item.score || 0) * 100)}%`;

    top.appendChild(rank);
    top.appendChild(score);

    const title = document.createElement("p");
    title.className = "track-title";
    title.textContent = item.title;

    const meta = document.createElement("p");
    meta.className = "track-meta";
    meta.textContent = `${item.artist} | ${tr("scoreLabel")}: ${Number(item.score).toFixed(4)}`;

    const why = document.createElement("p");
    why.className = "track-why";
    why.textContent = item.why || tr("whyFallback");

    const isLongReason = why.textContent.length > 110;
    if (isLongReason) {
      why.classList.add("collapsed");
    }

    const actions = document.createElement("div");
    actions.className = "track-actions";

    {
      const hasPreview = Boolean(item.preview_url);
      const previewCluster = document.createElement("div");
      previewCluster.className = "preview-cluster";
      if (!hasPreview) {
        previewCluster.classList.add("is-unavailable");
      }

      const previewBtn = document.createElement("button");
      previewBtn.type = "button";
      previewBtn.className = "preview-btn";
      previewBtn.setAttribute("aria-pressed", "false");
      previewBtn.setAttribute("aria-label", tr("previewAriaPlay"));
      previewBtn.textContent = tr("previewPlay");

      const previewMeter = document.createElement("div");
      previewMeter.className = "preview-meter";
      previewMeter.setAttribute("role", "progressbar");
      previewMeter.setAttribute("aria-label", tr("previewAriaMeter"));
      previewMeter.setAttribute("aria-valuemin", "0");
      previewMeter.setAttribute("aria-valuemax", "100");
      previewMeter.setAttribute("aria-valuenow", "0");

      const previewMeterFill = document.createElement("span");
      previewMeterFill.className = "preview-meter-fill";
      previewMeter.appendChild(previewMeterFill);

      const previewTime = document.createElement("div");
      previewTime.className = "preview-time";

      const elapsed = document.createElement("span");
      elapsed.textContent = "0:00";

      const duration = document.createElement("span");
      duration.textContent = hasPreview ? `0:30 ${tr("previewLabel")}` : tr("previewUnavailable");

      previewTime.appendChild(elapsed);
      previewTime.appendChild(duration);

      if (!hasPreview) {
        previewBtn.disabled = true;
        previewBtn.setAttribute("aria-label", tr("previewAriaUnavailable"));
        previewBtn.textContent = tr("previewNoPreview");
      }

      previewCluster.appendChild(previewBtn);
      previewCluster.appendChild(previewMeter);
      previewCluster.appendChild(previewTime);

      if (hasPreview) {
        previewBtn.addEventListener("click", () => {
        const isCurrent = currentPreviewButton === previewBtn;

        if (isCurrent && currentPreviewAudio && !currentPreviewAudio.paused) {
          currentPreviewAudio.pause();
          resetCurrentPreviewUI();
          return;
        }

        clearCurrentPreviewState();

        const audio = new Audio(item.preview_url);
        audio.volume = 0.95;
        audio.preload = "metadata";

        audio.addEventListener("loadedmetadata", () => {
          if (duration) {
            duration.textContent = `${formatPreviewTime(audio.duration || 30)} ${tr("previewLabel")}`;
          }
        });

        audio.addEventListener("ended", () => {
          resetCurrentPreviewUI();
          if (currentPreviewButton === previewBtn) {
            currentPreviewButton = null;
            currentPreviewAudio = null;
            currentPreviewCard = null;
            currentPreviewProgressFill = null;
            currentPreviewElapsed = null;
            currentPreviewDuration = null;
          }
        });

        audio.addEventListener("pause", () => {
          if (audio.ended) return;
          if (currentPreviewButton === previewBtn) {
            resetCurrentPreviewUI();
          }
        });

        audio
          .play()
          .then(() => {
            currentPreviewAudio = audio;
            currentPreviewButton = previewBtn;
            currentPreviewCard = card;
            currentPreviewProgressFill = previewMeterFill;
            currentPreviewElapsed = elapsed;
            currentPreviewDuration = duration;
            currentPreviewMeter = previewMeter;
            previewBtn.setAttribute("aria-pressed", "true");
            previewBtn.setAttribute("aria-label", tr("previewAriaPause"));
            previewBtn.textContent = tr("previewPause");
            card.classList.add("is-preview-playing");
            updatePreviewProgressUI();
          })
          .catch(() => {
            setStatus(tr("previewAutoplayError"), true);
            previewBtn.setAttribute("aria-pressed", "false");
            previewBtn.setAttribute("aria-label", tr("previewAriaPlay"));
            previewBtn.textContent = tr("previewPlay");
          });
        });
      }

      actions.appendChild(previewCluster);
    }

    const detailBtn = document.createElement("button");
    detailBtn.className = "text-btn";
    detailBtn.type = "button";
    detailBtn.textContent = tr("detailButton");
    detailBtn.addEventListener("click", () => {
      openTrackDetailModal(item);
    });
    actions.appendChild(detailBtn);

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
      link.textContent = tr("openSpotify");
      actions.appendChild(link);
    }

    if (actions.childElementCount > 0) {
      card.appendChild(actions);
    }

    recommendationList.appendChild(card);
  });

  if (list.length > 0) {
    const exportContainer = document.createElement("div");
    exportContainer.id = "exportActionBar";
    exportContainer.className = "export-action-bar";

    const exportBtn = document.createElement("button");
    exportBtn.className = "shimmer-btn";
    exportBtn.classList.add("export-action-btn");

    exportBtn.onmouseover = () => { exportBtn.style.transform = "scale(1.05)"; };
    exportBtn.onmouseout = () => { exportBtn.style.transform = "scale(1)"; };

    const hasToken = !!localStorage.getItem("spotify_token");
    exportBtn.textContent = hasToken ? tr("exportSave") : tr("exportLogin");

    exportBtn.addEventListener("click", async () => {
      if (!hasToken) {
        window.location.href = "/auth/login";
        return;
      }
      
      exportBtn.disabled = true;
      exportBtn.textContent = tr("exportCreating");
      exportBtn.style.opacity = "0.7";
      
      try {
        const trackIds = list
          .filter((i) => i.spotify_url && i.spotify_url.includes("/track/"))
          .map((i) => i.spotify_url.split("/track/")[1].split("?")[0]);
          
        const payload = {
          user_token: localStorage.getItem("spotify_token"),
          title: buildPlaylistTitle(data, sourceText),
          description: buildPlaylistDescription(data, sourceText),
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
              spotifyLoginBtn.textContent = tr("connectSpotify");
              spotifyLoginBtn.style.backgroundColor = "transparent";
              spotifyLoginBtn.style.border = "1px solid rgba(255,255,255,0.2)";
              spotifyLoginBtn.style.color = "#ccc";
              spotifyLoginBtn.disabled = false;
            }
            throw new Error(tr("spotifyExpired"));
          }

          throw new Error(
            resData.detail || resData.error || `Failed to create playlist (${res.status})`
          );
        }

        if (resData.url) {
          exportBtn.textContent = tr("exportCreated");
          exportBtn.style.opacity = "1";
          exportBtn.onclick = () => window.open(resData.url, "_blank");
          exportBtn.disabled = false;
          setStatus(tr("exportSuccessStatus"), false);
        } else {
          throw new Error(resData.error || tr("genericFailedPlaylist"));
        }
      } catch (err) {
        exportBtn.textContent = tr("exportErrorTryAgain");
        exportBtn.disabled = false;
        exportBtn.style.opacity = "1";
        exportBtn.style.backgroundColor = "#ff8f8f"; // error red
        setStatus(tr("exportFailed", { error: err.message }), true);
      }
    });

    exportContainer.appendChild(exportBtn);
    if (resultsPanel) {
      resultsPanel.insertBefore(exportContainer, recommendationList);
    } else {
      recommendationList.prepend(exportContainer);
    }
  }
}

function renderLoadingSkeleton(targetCount) {
  lastRenderedData = null;
  lastRenderedSourceText = "";
  clearCurrentPreviewState();
  const count = Math.max(4, Math.min(Number(targetCount) || 6, 8));
  recommendationList.innerHTML = "";
  resultLead.textContent = tr("loadingLead");

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
    setStatus(tr("intentRequired"), true);
    return;
  }

  submitBtn.disabled = true;
  setStatus(tr("searching"));
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
    renderRecommendations(data, text);

    const quality = data.quality_notes || {};
    const profilerMode = quality.llm_profiler_used ? "LLM" : "heuristic";
    const rankerMode = quality.llm_ranker_used ? "LLM" : "heuristic";

    setStatus(
      tr("foundStatus", { count: data.summary.returned_count, profilerMode, rankerMode })
    );
    stopAgentAnimation(true, data.quality_notes?.stage_ms || null);
  } catch (error) {
    setStatus(error.message || tr("requestErrorDefault"), true);
    recommendationList.innerHTML = `<p class=\"empty-state\">${tr("loadError")}</p>`;
    resultLead.textContent = tr("loadErrorLead");
    stopAgentAnimation(false);
  } finally {
    submitBtn.disabled = false;
  }
}

async function checkLlmHealth(showStatusMessage = false) {
  setLlmBadge(tr("llmChecking"), "neutral");

  try {
    const response = await fetch("/llm/health");
    if (!response.ok) {
      throw new Error(`LLM health failed (${response.status})`);
    }
    const data = await response.json();
    const model = data.model || "unknown-model";

    if (data.ok) {
      setLlmBadge(tr("llmOnline", { model }), "ok");
      if (showStatusMessage) {
        setStatus(tr("llmReadyStatus", { model }));
      }
      return;
    }

    const isDisabled = data.status === "disabled";
    setLlmBadge(
      isDisabled ? tr("llmDisabled") : tr("llmDegraded"),
      isDisabled ? "warn" : "error"
    );

    if (showStatusMessage) {
      setStatus(tr("llmStatus", { status: data.status, details: data.details || "" }).trim(), !isDisabled);
    }
  } catch (error) {
    setLlmBadge(tr("llmUnreachable"), "error");
    if (showStatusMessage) {
      setStatus(error.message || tr("llmHealthError"), true);
    }
  }
}

async function checkSpotifyHealth() {
  healthBtn.disabled = true;
  setStatus(tr("spotifyCheckingStatus"));

  try {
    const response = await fetch("/spotify/health");
    if (!response.ok) {
      throw new Error(`Spotify health failed (${response.status})`);
    }
    const data = await response.json();
    const detail = data.details ? ` ${data.details}` : "";
    if (data.ok) {
      setSpotifyBadge(tr("spotifyOnline"), "ok");
    } else if (data.status === "mock-mode") {
      setSpotifyBadge(tr("spotifyMock"), "warn");
    } else {
      setSpotifyBadge(tr("spotifyDegraded"), "error");
    }
    setStatus(tr("spotifyStatus", { status: data.status, detail }));
  } catch (error) {
    setSpotifyBadge(tr("spotifyUnreachable"), "error");
    setStatus(error.message || tr("spotifyHealthError"), true);
  } finally {
    healthBtn.disabled = false;
  }
}

function bindQuickPrompts() {
  if (!quickPrompts) {
    return;
  }

  quickPrompts.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }

    const button = target.closest("button");
    if (!(button instanceof HTMLButtonElement)) {
      return;
    }

    const fallbackIntent = button.dataset.intent;
    const intent = currentLang === "id"
      ? (button.dataset.intentId || fallbackIntent)
      : (button.dataset.intentEn || fallbackIntent || button.dataset.intentId);

    if (!intent) {
      return;
    }
    intentInput.value = intent;
    intentInput.focus();
    setStatus(tr("promptFilled"));
  });
}

function handleOAuthToken() {
  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get("token");
  if (token) {
    localStorage.setItem("spotify_token", token);
    window.history.replaceState({}, document.title, window.location.pathname);
    setStatus(tr("oauthSuccess"));
  }
  
  if (localStorage.getItem("spotify_token") && spotifyLoginBtn) {
    spotifyLoginBtn.textContent = tr("spotifyConnected");
    spotifyLoginBtn.style.backgroundColor = "transparent";
    spotifyLoginBtn.style.border = "1px solid #1DB954";
    spotifyLoginBtn.style.color = "#1DB954";
    spotifyLoginBtn.disabled = true;
  }
}

// ========================================
// Prompt History Autocomplete (Ultra Fast)
// ========================================
let promptSuggestionsDebounceTimer = null;
let promptSuggestionsCache = new Map(); // Cache results
let allPromptSuggestions = []; // Preloaded recent prompts

async function fetchPromptSuggestions(query) {
  // Check cache first
  if (promptSuggestionsCache.has(query)) {
    return promptSuggestionsCache.get(query);
  }

  try {
    const response = await fetch(`/api/prompt-suggestions?q=${encodeURIComponent(query)}`);
    if (!response.ok) return [];
    const data = await response.json();
    const suggestions = data.suggestions || [];
    
    // Cache the result
    promptSuggestionsCache.set(query, suggestions);
    return suggestions;
  } catch (e) {
    console.warn("Failed to fetch prompt suggestions:", e);
    return [];
  }
}

async function preloadRecentPrompts() {
  // Load all recent prompts once when app starts
  try {
    const response = await fetch(`/api/prompt-suggestions`);
    if (!response.ok) return;
    const data = await response.json();
    allPromptSuggestions = data.suggestions || [];
    promptSuggestionsCache.set("", allPromptSuggestions); // Cache empty query
  } catch (e) {
    console.warn("Failed to preload recent prompts:", e);
  }
}

function updatePromptDatalist(suggestions) {
  const dropdown = document.getElementById("promptSuggestions");
  if (!dropdown) return;
  
  if (!suggestions || suggestions.length === 0) {
    dropdown.style.display = "none";
    dropdown.innerHTML = "";
    return;
  }

  // Use DocumentFragment for faster DOM insertion
  const fragment = document.createDocumentFragment();
  
  suggestions.forEach((suggestion) => {
    const item = document.createElement("div");
    item.className = "prompt-suggestion-item";
    item.textContent = suggestion;
    item.dataset.prompt = suggestion;
    fragment.appendChild(item);
  });
  
  dropdown.innerHTML = "";
  dropdown.appendChild(fragment);
  dropdown.style.display = "block";
}

// Event delegation for suggestion clicks
document.addEventListener("click", (e) => {
  const item = e.target.closest(".prompt-suggestion-item");
  if (item && document.getElementById("intentInput")) {
    intentInput.value = item.dataset.prompt;
    document.getElementById("promptSuggestions").style.display = "none";
  }
});

// Event delegation for hover effects
document.addEventListener("mouseover", (e) => {
  const item = e.target.closest(".prompt-suggestion-item");
  if (item) {
    item.classList.add("hover");
    // Remove hover from siblings
    item.parentElement?.querySelectorAll(".prompt-suggestion-item").forEach(el => {
      if (el !== item) el.classList.remove("hover");
    });
  }
});

document.addEventListener("mouseout", (e) => {
  const item = e.target.closest(".prompt-suggestion-item");
  if (item && !e.relatedTarget?.closest(".prompt-suggestion-item")) {
    item.classList.remove("hover");
  }
});

function handlePromptInput(event) {
  const query = event.target.value.trim();
  
  // Clear previous debounce timer
  if (promptSuggestionsDebounceTimer) {
    clearTimeout(promptSuggestionsDebounceTimer);
  }

  // If input is empty, show preloaded recent prompts instantly
  if (!query) {
    updatePromptDatalist(allPromptSuggestions);
    return;
  }

  // Debounce fetch: wait 100ms after user stops typing (reduced from 300ms)
  promptSuggestionsDebounceTimer = setTimeout(async () => {
    const suggestions = await fetchPromptSuggestions(query);
    updatePromptDatalist(suggestions);
  }, 100);
}

// Close dropdown when clicking outside
document.addEventListener("click", (e) => {
  const dropdown = document.getElementById("promptSuggestions");
  const textarea = document.getElementById("intentInput");
  if (dropdown && !dropdown.contains(e.target) && !textarea?.contains(e.target)) {
    dropdown.style.display = "none";
  }
});

// Preload recent prompts on textarea focus
if (intentInput) {
  intentInput.addEventListener("focus", async () => {
    if (allPromptSuggestions.length === 0) {
      await preloadRecentPrompts();
      updatePromptDatalist(allPromptSuggestions);
    } else {
      // Show preloaded suggestions if textarea is empty
      if (!intentInput.value.trim()) {
        updatePromptDatalist(allPromptSuggestions);
      }
    }
  });
}

if (spotifyLoginBtn) {
  spotifyLoginBtn.addEventListener("click", () => {
    window.location.href = "/auth/login";
  });
}

form.addEventListener("submit", requestRecommendations);
if (intentInput) {
  intentInput.addEventListener("input", handlePromptInput);
}
healthBtn.addEventListener("click", checkSpotifyHealth);
bindLanguageSwitch();
bindTrackDetailModal();
applyLanguageUI();
bindQuickPrompts();
bindRuntimePreferences();
bindPipelineGeometrySync();
startRuntimeFrameLoop();
checkLlmHealth();
checkSpotifyHealth();
handleOAuthToken();
setAgentStage(0, tr("stageIdle"));
setAgentMetrics(tr("metricsDefault"));
