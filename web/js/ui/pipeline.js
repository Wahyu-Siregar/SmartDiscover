import { $ } from "../utils/dom.js";
import { tr } from "../i18n.js";

/**
 * Pipeline visualization — declarative + optimistic timeline.
 *
 * Visuals are CSS-keyframe driven (see pipeline.css), keyed off the
 * `data-stage` attribute on the agent orb. The orchestration layer
 * advances stages *while the request is in flight* using an optimistic
 * schedule learned from prior runs (stored in localStorage).
 */

const STAGE_TEXTS = {
  0: "stageIdle",
  1: "stageProfiler",
  2: "stageSearch",
  3: "stageRanker",
  4: "stagePresenter",
};

const STEP_IDS = ["pillProfiler", "pillSearch", "pillRanker", "pillPresenter"];

const TIMING_KEY = "smartdiscover_stage_ms";
const DEFAULT_TIMINGS = {
  profiler: 3000,
  search: 2500,
  ranker: 3500,
  presenter: 800,
};
const MIN_STAGE_MS = 350;   // never advance faster than this (UI clarity)
const MAX_STAGE_MS = 9000;  // never linger longer than this on a single stage

// ---- Stage / metrics setters --------------------------------------

export function setAgentStage(stage, text) {
  const flow = $("agentFlow");
  const orb = $("agentPixel");
  const stageText = $("agentStageText");

  if (flow) flow.dataset.stage = String(stage);
  if (orb) {
    orb.dataset.stage = String(stage);
    if (stage !== -1) orb.classList.remove("is-done");
  }
  if (stageText) stageText.textContent = text || tr(STAGE_TEXTS[stage] || "stageIdle");

  STEP_IDS.forEach((id, i) => {
    const node = $(id);
    if (!node) return;
    const n = i + 1;
    node.classList.toggle("active", n === stage);
    node.classList.toggle("done", stage > 0 && n < stage);
  });

  syncGeometry(stage);
}

function setAgentDone(text) {
  const orb = $("agentPixel");
  const stageText = $("agentStageText");
  if (orb) orb.classList.add("is-done");
  if (stageText) stageText.textContent = text || tr("stageDone");
  STEP_IDS.forEach((id) => {
    const node = $(id);
    if (!node) return;
    node.classList.remove("active");
    node.classList.add("done");
  });
  syncGeometry(4);
}

export function setAgentMetrics(text) {
  const node = $("agentMetrics");
  if (node) node.textContent = text;
}

export function setPipelineWorking(working) {
  const flow = $("agentFlow");
  if (flow) flow.classList.toggle("is-working", !!working);
}

export function getStageText(stage) {
  return tr(STAGE_TEXTS[stage] || "stageIdle");
}

// ---- Timing memory (learn from prior runs) ------------------------

function loadTimings() {
  try {
    const raw = localStorage.getItem(TIMING_KEY);
    if (!raw) return { ...DEFAULT_TIMINGS };
    const parsed = JSON.parse(raw);
    return {
      profiler: clampMs(parsed.profiler, DEFAULT_TIMINGS.profiler),
      search: clampMs(parsed.search, DEFAULT_TIMINGS.search),
      ranker: clampMs(parsed.ranker, DEFAULT_TIMINGS.ranker),
      presenter: clampMs(parsed.presenter, DEFAULT_TIMINGS.presenter),
    };
  } catch {
    return { ...DEFAULT_TIMINGS };
  }
}

function saveTimings(stageMs) {
  try {
    const prior = loadTimings();
    // Exponential moving average so a single slow run does not dominate.
    const ema = (next, prev) => {
      const n = clampMs(next, prev);
      return Math.round(0.6 * prev + 0.4 * n);
    };
    const updated = {
      profiler: ema(stageMs.profiler, prior.profiler),
      search: ema(stageMs.search, prior.search),
      ranker: ema(stageMs.ranker, prior.ranker),
      presenter: ema(stageMs.presenter, prior.presenter),
    };
    localStorage.setItem(TIMING_KEY, JSON.stringify(updated));
  } catch { /* localStorage may be disabled; non-fatal */ }
}

function clampMs(value, fallback) {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) return fallback;
  return Math.max(MIN_STAGE_MS, Math.min(MAX_STAGE_MS, n));
}

// ---- Optimistic timeline controller -------------------------------

/**
 * Start the optimistic timeline. Returns a controller that the caller
 * MUST eventually call .finalize() or .cancel() on.
 */
export function startAgentTimeline() {
  const timings = loadTimings();
  // Pad each predicted ms a touch so a fast backend doesn't overshoot us.
  const schedule = [
    { stage: 1, key: "profiler" },
    { stage: 2, key: "search" },
    { stage: 3, key: "ranker" },
    { stage: 4, key: "presenter" },
  ];

  setPipelineWorking(true);
  setAgentStage(1, tr("stageProfiler"));

  let cancelled = false;
  let timer = 0;
  let currentIndex = 0;
  const startedAt = performance.now();

  const advance = () => {
    if (cancelled) return;
    currentIndex += 1;
    if (currentIndex >= schedule.length) return; // stay on presenter
    const next = schedule[currentIndex];
    setAgentStage(next.stage, tr(STAGE_TEXTS[next.stage]));
    timer = window.setTimeout(advance, clampMs(timings[next.key], DEFAULT_TIMINGS[next.key]));
  };

  // First scheduled hop after profiler's predicted window.
  timer = window.setTimeout(advance, clampMs(timings.profiler, DEFAULT_TIMINGS.profiler));

  function clear() {
    cancelled = true;
    if (timer) { window.clearTimeout(timer); timer = 0; }
  }

  return {
    /**
     * Successful response — snap to Done with a brief catch-up if we
     * lagged behind the backend.
     */
    finalize(stageMs = {}, doneText) {
      clear();
      const totalElapsed = performance.now() - startedAt;
      saveTimings(stageMs);

      // If we never even reached presenter visually, do a quick catch-up.
      const flow = $("agentFlow");
      const visualStage = Number(flow?.dataset?.stage || 1);
      const remaining = Math.max(0, 4 - visualStage);
      const catchupBudget = Math.min(900, 220 * remaining);

      const finishWith = () => setAgentDone(doneText || tr("stageDone"));

      if (remaining === 0) {
        // Already at presenter visually — small grace pause then done.
        window.setTimeout(finishWith, 220);
      } else {
        // Walk through any missing stages quickly.
        const stepMs = remaining > 0 ? Math.max(180, catchupBudget / remaining) : 0;
        let i = visualStage;
        const tick = () => {
          i += 1;
          if (i > 4) return finishWith();
          setAgentStage(i, tr(STAGE_TEXTS[i] || "stagePresenter"));
          window.setTimeout(tick, stepMs);
        };
        window.setTimeout(tick, 120);
      }

      // Tail message for the metrics line.
      setPipelineWorkingAfter(false, 1200);
      return { totalElapsed, stageMs };
    },

    /**
     * Error path — stop animation, mark as stopped.
     */
    cancel(reasonText) {
      clear();
      const stageText = $("agentStageText");
      if (stageText) stageText.textContent = reasonText || tr("stageStopped");
      setPipelineWorking(false);
    },
  };
}

function setPipelineWorkingAfter(working, delayMs) {
  window.setTimeout(() => setPipelineWorking(working), delayMs);
}

// Backwards-compat shim for legacy callers.
export function startPipelineLoop() { /* CSS-driven, nothing to start */ }

/**
 * Legacy replay helper kept for non-form code paths (e.g. /refine).
 * It performs a fast forward sequence using the actual stage_ms.
 */
export async function replayStagesFromMetrics(stageMs, doneText) {
  const sequence = [
    [1, tr("stageProfiler"), Number(stageMs?.profiler || 0)],
    [2, tr("stageSearch"), Number(stageMs?.search || 0)],
    [3, tr("stageRanker"), Number(stageMs?.ranker || 0)],
    [4, tr("stagePresenter"), Number(stageMs?.presenter || 0)],
  ];
  setPipelineWorking(true);
  for (const [stage, text, ms] of sequence) {
    setAgentStage(stage, text);
    await delay(Math.min(700, Math.max(180, ms || 220)));
  }
  setAgentDone(doneText || tr("stageDone"));
  setPipelineWorkingAfter(false, 800);
}

function delay(ms) { return new Promise((r) => setTimeout(r, ms)); }

// ---- Geometry sync (orb position along the track) -----------------

function syncGeometry(stage) {
  const container = document.querySelector(".track-container");
  const orb = $("agentPixel");
  const trackActive = document.querySelector(".track-active");
  if (!container || !orb || !trackActive) return;

  const containerRect = container.getBoundingClientRect();
  const dotXs = STEP_IDS
    .map((id) => $(id))
    .filter(Boolean)
    .map((p) => {
      const dot = p.querySelector(".dot");
      if (!dot) return null;
      const r = dot.getBoundingClientRect();
      return r.left - containerRect.left + r.width / 2;
    })
    .filter((v) => v !== null);

  if (!dotXs.length) return;

  let targetX = 0;
  if (stage <= 0) {
    targetX = dotXs.length > 1
      ? Math.max(0, dotXs[0] - (dotXs[1] - dotXs[0]) * 0.6)
      : Math.max(0, dotXs[0] - 18);
  } else {
    targetX = dotXs[Math.min(stage - 1, dotXs.length - 1)];
  }

  orb.style.left = `${targetX}px`;
  trackActive.style.width = `${Math.max(0, targetX)}px`;
}

export function bindPipelineGeometry() {
  let rafId = 0;
  const resync = () => {
    if (rafId) cancelAnimationFrame(rafId);
    rafId = requestAnimationFrame(() => {
      const flow = $("agentFlow");
      const stage = Number(flow?.dataset?.stage || 0);
      syncGeometry(Number.isFinite(stage) ? stage : 0);
    });
  };
  window.addEventListener("resize", resync, { passive: true });
  resync();
}
