import { $ } from "../utils/dom.js";
import { tr } from "../i18n.js";

export function applyDossierLabels() {
  setText("dossierTitle", tr("dossierTitle"));
  setText("insightEngineLabel", tr("insightEngineLabel"));
  setText("insightEngineValue", tr("insightEngineValue"));
  setText("insightLatencyLabel", tr("insightLatencyLabel"));
  setText("insightLatencyValue", tr("insightLatencyValue"));
  setText("insightOutputLabel", tr("insightOutputLabel"));
  setText("insightOutputValue", tr("insightOutputValue"));
}

export function setDossierMode(mode) {
  setText("dossierMode", mode || "Idle");
}

export function setDossierLatency(ms) {
  if (ms == null) return setText("insightLatencyValue", tr("insightLatencyValue"));
  setText("insightLatencyValue", `${ms} ms`);
}

function setText(id, text) {
  const node = $(id);
  if (node) node.textContent = text;
}
