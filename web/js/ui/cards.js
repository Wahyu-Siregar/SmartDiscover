import { el, $, clearChildren } from "../utils/dom.js";
import { formatPercent, pad2 } from "../utils/format.js";
import { tr } from "../i18n.js";
import { renderAudioChips } from "./audioChips.js";
import { renderPreview, stopAllPreviews } from "./preview.js";
import { openModal } from "./modal.js";

export function renderTrackCards(items) {
  const list = $("recommendationList");
  if (!list) return;
  stopAllPreviews();
  clearChildren(list);

  if (!items || !items.length) {
    list.appendChild(el("p", { class: "empty-state", text: tr("emptyNoRecommendation") }));
    return;
  }

  items.forEach((item, idx) => {
    list.appendChild(buildCard(item, idx + 1));
  });
}

function buildCard(item, rank) {
  const card = el("article", { class: "track-card" });

  card.appendChild(el("span", { class: "track-card__num", text: pad2(rank) }));

  card.appendChild(el("div", { class: "track-card__head" }, [
    el("h3", { class: "track-card__title", text: item.title || "—" }),
    el("p", { class: "track-card__artist", text: item.artist || "—" }),
  ]));

  card.appendChild(el("div", { class: "track-card__score" }, [
    el("span", { class: "track-card__score-num", text: formatPercent(item.score, 0) }),
    el("span", { class: "track-card__score-label", text: tr("matchLabel") }),
  ]));

  card.appendChild(el("p", {
    class: "track-card__why",
    text: item.why?.trim() || tr("whyFallback"),
    onClick: () => openModal(item),
  }));

  // Footer: audio chips left, actions right.
  const footer = el("div", { class: "track-card__footer" });
  const chips = renderAudioChips(item.audio_features);
  const lyricChip = renderLyricChip(item.lyric_signals);
  const chipWrap = el("div", { class: "audio-chips" });
  if (chips) Array.from(chips.children).forEach((child) => chipWrap.appendChild(child));
  if (lyricChip) chipWrap.appendChild(lyricChip);
  footer.appendChild(chipWrap.children.length ? chipWrap : el("span"));

  const actions = el("div", { class: "track-card__actions" }, [
    renderPreview(item, card),
  ]);

  if (item.spotify_url) {
    actions.appendChild(el("a", {
      class: "modal__link",
      href: item.spotify_url,
      target: "_blank",
      rel: "noopener noreferrer",
      text: tr("openSpotify"),
    }));
  }

  actions.appendChild(el("button", {
    type: "button",
    class: "icon-btn",
    "aria-label": tr("detailButton"),
    title: tr("detailButton"),
    onClick: () => openModal(item),
    text: "›",
  }));

  footer.appendChild(actions);
  card.appendChild(footer);
  return card;
}

function renderLyricChip(signals) {
  if (!signals || typeof signals !== "object") return null;
  const score = Number(signals.match_score);
  const themes = Array.isArray(signals.themes) ? signals.themes.slice(0, 2).join(", ") : "";
  return el("span", {
    class: "audio-chip",
    title: signals.summary || themes || tr("lyricSignal"),
  }, [
    el("span", { class: "audio-chip__icon", text: "♪" }),
    el("span", { text: Number.isFinite(score) ? `${tr("lyricSignal")} ${formatPercent(score)}` : tr("lyricSignal") }),
  ]);
}
