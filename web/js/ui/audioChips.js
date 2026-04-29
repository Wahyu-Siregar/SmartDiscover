import { el } from "../utils/dom.js";
import { formatPercent, formatTempo, valenceEmoji } from "../utils/format.js";
import { tr } from "../i18n.js";

export function renderAudioChips(audioFeatures) {
  if (!audioFeatures || typeof audioFeatures !== "object") return null;

  const energy = Number(audioFeatures.energy);
  const valence = Number(audioFeatures.valence);
  const tempo = Number(audioFeatures.tempo);

  const chips = el("div", { class: "audio-chips", "aria-label": "Audio features" });

  if (Number.isFinite(energy)) {
    chips.appendChild(el("span", { class: "audio-chip audio-chip--energy", title: `${tr("audioEnergy")} ${formatPercent(energy)}` }, [
      el("span", { class: "audio-chip__icon", text: "⚡" }),
      el("span", {
        class: "audio-chip__bar",
        "aria-hidden": "true",
      }, [
        el("span", { class: "audio-chip__bar-fill", style: { width: `${Math.round(energy * 100)}%` } }),
      ]),
      el("span", { text: formatPercent(energy) }),
    ]));
  }

  if (Number.isFinite(valence)) {
    chips.appendChild(el("span", { class: "audio-chip audio-chip--valence", title: `${tr("audioMood")} ${formatPercent(valence)}` }, [
      el("span", { class: "audio-chip__icon", text: valenceEmoji(valence) }),
      el("span", { text: formatPercent(valence) }),
    ]));
  }

  if (Number.isFinite(tempo) && tempo > 0) {
    chips.appendChild(el("span", { class: "audio-chip audio-chip--tempo", title: tr("audioTempo") }, [
      el("span", { class: "audio-chip__icon", text: "♩" }),
      el("span", { text: formatTempo(tempo) }),
    ]));
  }

  return chips.children.length ? chips : null;
}
