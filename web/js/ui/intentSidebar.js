import { $, setHidden } from "../utils/dom.js";
import { tr } from "../i18n.js";
import { formatPercent } from "../utils/format.js";

export function applyIntentLabels() {
  const map = {
    intentCardEyebrow: tr("intentDetected"),
    statMoodLabel: tr("statMood"),
    statActivityLabel: tr("statActivity"),
    statCountLabel: tr("statCount"),
    statModeLabel: tr("statMode"),
  };
  for (const [id, text] of Object.entries(map)) {
    const node = $(id);
    if (node) node.textContent = text;
  }
}

export function renderIntentSidebar(data, sourceText) {
  const card = $("intentCard");
  if (!card) return;
  if (!data) {
    setHidden(card, true);
    return;
  }
  setHidden(card, false);

  const profile = data.intent_profile || {};
  const summary = data.summary || {};
  const notes = data.quality_notes || {};

  applyIntentLabels();

  const headline = $("intentCardHeadline");
  if (headline) {
    const subj = (sourceText || summary.intent_text || "").trim();
    headline.innerHTML = subj
      ? `<em>${escapeHtml(truncate(subj, 80))}</em>`
      : "—";
  }

  setText("summaryMood", titleCase(profile.mood || "—"));
  setText("summaryActivity", titleCase(profile.activity || "—"));
  setText("summaryCount", String(summary.returned_count ?? "—"));

  const llmEnabled = !!notes.llm_enabled;
  setText("summaryMode", llmEnabled ? "LLM Hybrid" : "Heuristic");

  const fill = $("confidenceFill");
  if (fill) fill.style.width = formatPercent(profile.confidence ?? 0.5);
}

function setText(id, value) {
  const node = $(id);
  if (node) node.textContent = value;
}

function titleCase(s) {
  if (!s || typeof s !== "string") return "—";
  return s.replace(/[_-]+/g, " ").trim().split(/\s+/).map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

function truncate(s, n) {
  return s.length > n ? s.slice(0, n - 1).trimEnd() + "…" : s;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}
