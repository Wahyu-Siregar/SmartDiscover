import { $, clearChildren, el } from "./utils/dom.js";
import { initLang, setLanguage, currentLang, tr, onLangChange } from "./i18n.js";
import * as api from "./api.js";
import { bindModal, applyLabels as applyModalLabels } from "./ui/modal.js";
import {
  startPipelineLoop,
  bindPipelineGeometry,
  setAgentStage,
  setAgentMetrics,
  setPipelineWorking,
  startAgentTimeline,
} from "./ui/pipeline.js";
import { renderSkeleton } from "./ui/skeleton.js";
import { applyDossierLabels, setDossierLatency, setDossierMode } from "./ui/dossier.js";
import { applyIntentLabels } from "./ui/intentSidebar.js";
import { renderResultPayload, rerenderLast, setStatus, setResultLead } from "./render.js";
import { bindSpotifyButton, syncOAuthStatus, setSpotifyConnected } from "./oauth.js";
import { getState } from "./state.js";

// ---- Static label hookup (i18n) -----------------------------------

function applyStaticLabels() {
  const map = {
    heroKicker: "heroKicker",
    subtitleText: "subtitle",
    intentLabel: "intentLabel",
    targetCountLabel: "targetCountLabel",
    agenticModeLabel: "agenticModeLabel",
    submitText: "submit",
    quickPromptLabel: "quickPromptLabel",
    chipFocus: "chipFocus",
    chipRain: "chipRain",
    chipWorkout: "chipWorkout",
    healthBtn: "checkHealth",
    pipelineTitle: "pipelineTitle",
    resultsTitle: "resultsTitle",
    resultsKicker: "resultsKicker",
    resultsPill: "resultsPill",
    agenticPanelSummary: "behindScenes",
  };
  for (const [id, key] of Object.entries(map)) {
    const node = $(id);
    if (node) node.textContent = tr(key);
  }

  const heroTitle = $("heroTitle");
  if (heroTitle) heroTitle.innerHTML = tr("heroTitle");

  const intentInput = $("intentInput");
  if (intentInput) intentInput.setAttribute("placeholder", tr("intentPlaceholder"));

  const agenticOptions = {
    agenticModeAuto: "agenticAuto",
    agenticModeAgentic: "agenticForce",
    agenticModeLinear: "agenticLinear",
  };
  for (const [id, key] of Object.entries(agenticOptions)) {
    const node = $(id);
    if (node) node.textContent = tr(key);
  }

  // Spotify button
  const spotifyBtn = $("spotifyLoginBtn");
  if (spotifyBtn && !getState("spotifyConnected")) spotifyBtn.textContent = tr("connectSpotify");

  // Lang buttons aria
  const langId = $("langIdBtn");
  const langEn = $("langEnBtn");
  if (langId && langEn) {
    const isId = currentLang() === "id";
    langId.classList.toggle("is-active", isId);
    langEn.classList.toggle("is-active", !isId);
    langId.setAttribute("aria-pressed", String(isId));
    langEn.setAttribute("aria-pressed", String(!isId));
  }

  applyDossierLabels();
  applyIntentLabels();
  applyModalLabels();

  // Stage idle text refresh
  setAgentStage(0, tr("stageIdle"));
}

function bindLang() {
  const wrap = $("langSwitch");
  if (!wrap) return;
  wrap.addEventListener("click", (e) => {
    const btn = e.target.closest(".lang-btn");
    if (!btn) return;
    if (btn.id === "langIdBtn") setLanguage("id");
    else if (btn.id === "langEnBtn") setLanguage("en");
  });
}

function bindQuickPrompts() {
  const wrap = $("quickPrompts");
  if (!wrap) return;
  wrap.addEventListener("click", (e) => {
    const btn = e.target.closest(".chip");
    if (!btn) return;
    const lang = currentLang();
    const intent = btn.dataset[`intent${lang === "id" ? "Id" : "En"}`] || btn.dataset.intentId || "";
    if (!intent) return;
    const input = $("intentInput");
    if (input) {
      input.value = intent;
      input.focus();
    }
    setStatus(tr("promptFilled"));
  });
}

function bindPromptSuggestions() {
  const input = $("intentInput");
  const dropdown = $("promptSuggestions");
  if (!input || !dropdown) return;

  const cache = new Map();
  let timer = 0;
  let activeIndex = -1;

  const close = () => {
    dropdown.classList.remove("is-open");
    activeIndex = -1;
  };

  const applyActive = () => {
    Array.from(dropdown.children).forEach((child, index) => {
      child.classList.toggle("is-active", index === activeIndex);
    });
  };

  const choose = (value) => {
    input.value = value;
    close();
    input.focus();
  };

  const render = (suggestions) => {
    clearChildren(dropdown);
    activeIndex = -1;
    if (!suggestions.length) {
      close();
      return;
    }

    suggestions.forEach((suggestion) => {
      dropdown.appendChild(el("button", {
        type: "button",
        class: "prompt-suggestion-item",
        role: "option",
        text: suggestion,
        onClick: () => choose(suggestion),
      }));
    });
    dropdown.classList.add("is-open");
  };

  const load = async (query) => {
    const key = query.trim().toLowerCase();
    if (cache.has(key)) {
      render(cache.get(key));
      return;
    }
    try {
      const data = await api.promptSuggestions(query);
      const suggestions = Array.isArray(data?.suggestions) ? data.suggestions : [];
      cache.set(key, suggestions);
      render(suggestions);
    } catch {
      render([]);
    }
  };

  input.addEventListener("focus", () => load(input.value.trim()));
  input.addEventListener("input", () => {
    if (timer) window.clearTimeout(timer);
    timer = window.setTimeout(() => load(input.value.trim()), 120);
  });
  input.addEventListener("keydown", (e) => {
    const items = Array.from(dropdown.children);
    if (!items.length || !dropdown.classList.contains("is-open")) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      activeIndex = (activeIndex + 1) % items.length;
      applyActive();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      activeIndex = (activeIndex - 1 + items.length) % items.length;
      applyActive();
    } else if (e.key === "Enter" && activeIndex >= 0) {
      e.preventDefault();
      choose(items[activeIndex].textContent || "");
    } else if (e.key === "Escape") {
      close();
    }
  });
  document.addEventListener("click", (e) => {
    if (e.target === input || dropdown.contains(e.target)) return;
    close();
  });
}

// ---- Form submission -----------------------------------------------

function bindForm() {
  const form = $("recommendForm");
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const intentInput = $("intentInput");
    const text = (intentInput?.value || "").trim();
    if (!text) {
      setStatus(tr("intentRequired"), true);
      return;
    }
    const targetEl = $("targetCountInput");
    const targetCount = Number(targetEl?.value) || 15;
    const agenticMode = $("agenticModeSelect")?.value || "auto";

    const submitBtn = $("submitBtn");
    if (submitBtn) submitBtn.disabled = true;

    setResultLead(tr("loadingLead"));
    setStatus(tr("searching"));
    renderSkeleton(targetCount);
    setAgentMetrics(tr("metricsWorking"));

    // Start optimistic pipeline timeline driven by past run averages.
    const timeline = startAgentTimeline();

    try {
      const data = await api.recommend({ text, target_count: targetCount, agentic_mode: agenticMode });
      // Hand the real backend timings to the timeline so it can finish
      // gracefully and refine its future estimates.
      timeline.finalize(data?.quality_notes?.stage_ms || {}, tr("stageDone"));
      renderResultPayload(data, text, { skipReplay: true });
    } catch (err) {
      timeline.cancel(tr("stageStopped"));
      setStatus(err.message || tr("loadError"), true);
      setResultLead(tr("loadErrorLead"));
      setAgentMetrics(tr("metricsError"));
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  });
}

// ---- Health checks -------------------------------------------------

async function checkLlmHealth() {
  setLlmBadge(tr("llmChecking"), "neutral");
  try {
    const data = await api.llmHealth();
    if (data.ok) {
      setLlmBadge(tr("llmOnline", { model: data.model || "" }), "ok");
    } else if (data.status === "disabled") {
      setLlmBadge(tr("llmDisabled"), "warn");
    } else {
      setLlmBadge(tr("llmDegraded"), "warn");
    }
  } catch {
    setLlmBadge(tr("llmUnreachable"), "error");
  }
}

async function checkSpotifyHealth() {
  setSpotifyBadge(tr("spotifyCheckingStatus"), "neutral");
  try {
    const data = await api.spotifyHealth();
    if (data.status === "ok") setSpotifyBadge(tr("spotifyOnline"), "ok");
    else if (data.status === "mock-mode") setSpotifyBadge(tr("spotifyMock"), "warn");
    else setSpotifyBadge(tr("spotifyDegraded"), "warn");
  } catch {
    setSpotifyBadge(tr("spotifyUnreachable"), "error");
  }
}

function setLlmBadge(text, tone = "neutral") {
  const node = $("llmBadge");
  if (!node) return;
  node.classList.remove("neutral", "ok", "warn", "error");
  node.classList.add(tone);
  node.textContent = text;
}

function setSpotifyBadge(text, tone = "neutral") {
  const node = $("spotifyBadge");
  if (!node) return;
  node.classList.remove("neutral", "ok", "warn", "error");
  node.classList.add(tone);
  node.textContent = text;
}

// ---- Bootstrap -----------------------------------------------------

function boot() {
  initLang();
  applyStaticLabels();
  bindLang();
  bindQuickPrompts();
  bindPromptSuggestions();
  bindForm();
  bindModal();
  bindSpotifyButton();
  startPipelineLoop();
  bindPipelineGeometry();
  setAgentStage(0, tr("stageIdle"));
  setAgentMetrics(tr("metricsDefault"));
  setDossierMode("Idle");
  setDossierLatency(null);

  $("healthBtn")?.addEventListener("click", () => {
    checkLlmHealth();
    checkSpotifyHealth();
  });

  // Re-apply labels on lang change.
  onLangChange(() => {
    applyStaticLabels();
    rerenderLast();
  });

  checkLlmHealth();
  checkSpotifyHealth();
  syncOAuthStatus();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot);
} else {
  boot();
}
