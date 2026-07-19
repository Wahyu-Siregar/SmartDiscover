import { $, el, clearChildren, setHidden } from "../utils/dom.js";
import { tr } from "../i18n.js";
import { getState } from "../state.js";

const WARNING_LABELS = {
  demo_catalog: "demoCatalogNotice",
  basic_matching: "basicMatchingNotice",
  low_profile_confidence: "qualityLowConfidence",
  candidate_pool_small: "qualitySmallPool",
  low_average_score: "qualityLowScore",
};

export function renderQualityWarnings(qualityNotes) {
  const banner = $("qualityWarnings");
  if (!banner) return;

  const warnings = [...(qualityNotes?.quality_warnings || [])];
  if (getState("spotifyStatus") === "mock-mode") warnings.unshift("demo_catalog");
  if (qualityNotes?.llm_enabled === false) warnings.unshift("basic_matching");
  if (!warnings.length) {
    setHidden(banner, true);
    clearChildren(banner);
    return;
  }

  clearChildren(banner);
  banner.appendChild(el("span", { class: "quality-banner__icon", text: "⚠" }));

  const list = el("div", { class: "quality-banner__list" });
  for (const w of warnings) {
    const key = String(w).split(" ")[0];
    const labelKey = WARNING_LABELS[key];
    const text = labelKey ? tr(labelKey) : String(w);
    list.appendChild(el("span", { text }));
  }
  banner.appendChild(list);
  setHidden(banner, false);
}
