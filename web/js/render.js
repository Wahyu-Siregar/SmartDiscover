import { $ } from "./utils/dom.js";
import { setState, getState } from "./state.js";
import { tr } from "./i18n.js";
import { renderTrackCards } from "./ui/cards.js";
import { renderIntentSidebar } from "./ui/intentSidebar.js";
import { renderQualityWarnings } from "./ui/qualityWarnings.js";
import { renderAgenticPanel } from "./ui/agenticPanel.js";
import { renderRefineBar } from "./ui/refineBar.js";
import { renderExportBar } from "./ui/exportBar.js";
import { setDossierLatency, setDossierMode } from "./ui/dossier.js";
import { replayStagesFromMetrics } from "./ui/pipeline.js";

export function setStatus(message, isError = false) {
  const node = $("statusText");
  if (!node) return;
  node.textContent = message;
  node.style.color = isError ? "var(--err)" : "var(--muted)";
}

export function setResultLead(text) {
  const node = $("resultLead");
  if (node) node.textContent = text;
}

export function renderResultPayload(data, sourceText, opts = {}) {
  if (!data) return;

  setState("lastResult", data);
  setState("lastSourceText", sourceText || data.summary?.intent_text || "");

  const recs = data.recommendations || [];
  const notes = data.quality_notes || {};

  setResultLead(
    recs.length
      ? tr("resultLeadFound", { count: recs.length })
      : tr("resultLeadNoResult")
  );

  setStatus(tr("foundStatus", {
    count: recs.length,
    profilerMode: notes.llm_profiler_used ? "LLM" : "heuristic",
    rankerMode: notes.llm_ranker_used ? "LLM" : "heuristic",
  }));

  renderIntentSidebar(data, sourceText);
  renderQualityWarnings(notes);
  renderExportBar(data, sourceText);
  renderRefineBar(data);
  renderTrackCards(recs);
  renderAgenticPanel(notes);

  // Dossier updates.
  setDossierLatency(notes.stage_ms?.total);
  setDossierMode(notes.llm_enabled ? (notes.agent_loop_enabled ? "Agent Loop" : "LLM Hybrid") : "Heuristic");

  // Pipeline replay only when called outside the form flow (e.g. /refine
  // or rerender on lang change). The form path runs an optimistic timeline.
  if (!opts.skipReplay) {
    replayStagesFromMetrics(notes.stage_ms || {}, tr("stageDone"));
  }
}

export function rerenderLast() {
  const data = getState("lastResult");
  const src = getState("lastSourceText");
  if (data) renderResultPayload(data, src, { skipReplay: true });
}
