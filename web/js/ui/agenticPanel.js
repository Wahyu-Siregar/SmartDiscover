import { $, el, clearChildren, setHidden } from "../utils/dom.js";
import { tr } from "../i18n.js";

const STAGE_KEYS = ["profiler", "search", "ranker", "presenter"];

export function renderAgenticPanel(qualityNotes) {
  const panel = $("agenticPanel");
  const summary = $("agenticPanelSummary");
  const body = $("agenticPanelBody");
  if (!panel || !body) return;

  if (!qualityNotes) {
    setHidden(panel, true);
    return;
  }

  if (summary) summary.textContent = tr("behindScenes");
  setHidden(panel, false);
  clearChildren(body);

  // 1) Stage timing bars.
  const stageMs = qualityNotes.stage_ms || {};
  const maxMs = Math.max(...STAGE_KEYS.map((k) => Number(stageMs[k] || 0)), 1);

  body.appendChild(el("p", { class: "agentic-panel__section-label", text: tr("stageMs") }));
  const grid = el("div", { class: "stage-bars" });
  for (const key of STAGE_KEYS) {
    const ms = Number(stageMs[key] || 0);
    grid.appendChild(el("span", { class: "stage-bars__name", text: key }));
    grid.appendChild(el("div", { class: "stage-bars__bar" }, [
      el("div", { class: "stage-bars__fill", style: { width: `${Math.max(2, (ms / maxMs) * 100)}%` } }),
    ]));
    grid.appendChild(el("span", { class: "stage-bars__time", text: `${ms} ms` }));
  }
  body.appendChild(grid);

  // 2) LLM usage flags.
  body.appendChild(el("p", { class: "agentic-panel__section-label", text: tr("llmUsage") }));
  const llmRow = el("div", { class: "cluster" });
  llmRow.appendChild(flag("Profiler", qualityNotes.llm_profiler_used));
  llmRow.appendChild(flag("Ranker", qualityNotes.llm_ranker_used));
  llmRow.appendChild(flag("Presenter", qualityNotes.llm_presenter_used));
  llmRow.appendChild(flag("Agent loop", qualityNotes.agent_loop_enabled));
  body.appendChild(llmRow);

  // 3) Cache hits.
  const cache = qualityNotes.cache_hits || {};
  if (Object.keys(cache).length) {
    body.appendChild(el("p", { class: "agentic-panel__section-label", text: tr("cacheHits") }));
    const cacheRow = el("div", { class: "cluster" });
    for (const [key, hit] of Object.entries(cache)) {
      cacheRow.appendChild(el("span", {
        class: hit ? "agentic-flag is-on" : "agentic-flag",
        text: `${key}: ${hit ? tr("cacheHit") : tr("cacheMiss")}`,
      }));
    }
    body.appendChild(cacheRow);
  }

  // 4) Agentic loop trace.
  const tools = qualityNotes.tools_called || [];
  const iterations = Number(qualityNotes.agent_iterations || 0);
  if (iterations > 0 || tools.length) {
    body.appendChild(el("p", { class: "agentic-panel__section-label", text: `${tr("agenticIterations")}: ${iterations}` }));
    if (tools.length) {
      const trace = el("div", { class: "agentic-trace" });
      tools.forEach((name, i) => {
        if (i > 0) trace.appendChild(el("span", { class: "agentic-trace__sep", text: "→" }));
        trace.appendChild(el("span", { class: "agentic-trace__step", text: name }));
      });
      body.appendChild(trace);
    }
  }

  // 5) Refined-from chip.
  if (qualityNotes.refined_from) {
    body.appendChild(el("div", { class: "cluster" }, [
      el("span", { class: "agentic-flag is-on", text: `${tr("refinedFrom")}: ${qualityNotes.refined_from}` }),
    ]));
  }
}

function flag(label, on) {
  return el("span", {
    class: on ? "agentic-flag is-on" : "agentic-flag",
    text: `${label} ${on ? "✓" : "—"}`,
  });
}
