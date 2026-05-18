import { $, el, clearChildren, setHidden } from "../utils/dom.js";
import { tr, currentLang } from "../i18n.js";
import * as api from "../api.js";
import { trackIdFromUrl } from "../utils/format.js";
import { renderResultPayload, setStatus } from "../render.js";

const SUGGESTIONS = ["refineMore", "refineLess", "refineLessInstrumental", "refineLocalOnly"];

export function renderRefineBar(data) {
  const slot = $("refineSlot");
  if (!slot) return;
  clearChildren(slot);

  if (!data || !(data.recommendations || []).length) {
    setHidden(slot, true);
    return;
  }
  setHidden(slot, false);

  const wrap = el("section", { class: "refine" });

  wrap.appendChild(el("div", { class: "refine__head" }, [
    el("span", { class: "refine__label", text: tr("refineLabel") }),
    el("span", { class: "refine__hint", text: tr("refineHint") }),
  ]));

  const input = el("input", {
    type: "text",
    class: "refine__input",
    placeholder: tr("refinePlaceholder"),
    maxLength: 200,
    "aria-label": tr("refineLabel"),
  });

  const btn = el("button", {
    type: "button",
    class: "btn btn--primary",
    text: tr("refineButton"),
  });

  const submit = async () => {
    const text = (input.value || "").trim();
    if (text.length < 3) return;
    btn.disabled = true;
    input.disabled = true;
    btn.textContent = tr("refining");

    try {
      const previousProfile = data.intent_profile || {};
      const previousTrackIds = (data.recommendations || [])
        .map((r) => r.track_id || trackIdFromUrl(r.spotify_url))
        .filter(Boolean);

      const refined = await api.refine({
        previous_profile: previousProfile,
        previous_track_ids: previousTrackIds,
        refinement_text: text,
        target_count: data.summary?.target_count || null,
        agentic_mode: $("agenticModeSelect")?.value || data.quality_notes?.agentic?.mode_requested || "auto",
      });

      renderResultPayload(refined, refined.summary?.intent_text || "");
      setStatus(tr("refineDone"));
    } catch (err) {
      setStatus(tr("refineFailed", { error: err.message || "" }), true);
    } finally {
      btn.disabled = false;
      input.disabled = false;
      btn.textContent = tr("refineButton");
    }
  };

  btn.addEventListener("click", submit);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") submit();
  });

  wrap.appendChild(el("div", { class: "refine__row" }, [input, btn]));

  const sugRow = el("div", { class: "refine__suggestions" });
  for (const key of SUGGESTIONS) {
    sugRow.appendChild(el("button", {
      type: "button",
      class: "chip chip--accent",
      text: tr(key),
      onClick: () => {
        input.value = tr(key);
        submit();
      },
    }));
  }
  wrap.appendChild(sugRow);

  slot.appendChild(wrap);
}
