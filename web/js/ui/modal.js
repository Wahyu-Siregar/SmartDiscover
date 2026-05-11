import { $ } from "../utils/dom.js";
import { tr } from "../i18n.js";
import { formatPercent } from "../utils/format.js";

let currentItem = null;

function refs() {
  return {
    modal: $("trackDetailModal"),
    overlay: $("trackDetailOverlay"),
    closeBtn: $("trackDetailCloseBtn"),
    title: $("trackDetailTitle"),
    song: $("trackDetailSong"),
    artist: $("trackDetailArtist"),
    scoreLabel: $("trackDetailScoreLabel"),
    scoreVal: $("trackDetailScoreValue"),
    previewLabel: $("trackDetailPreviewLabel"),
    previewVal: $("trackDetailPreviewValue"),
    reasonLabel: $("trackDetailReasonLabel"),
    reasonText: $("trackDetailReasonText"),
    link: $("trackDetailSpotifyLink"),
  };
}

export function bindModal() {
  const r = refs();
  if (r.overlay) r.overlay.addEventListener("click", closeModal);
  if (r.closeBtn) r.closeBtn.addEventListener("click", closeModal);
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
  });
  applyLabels();
}

export function applyLabels() {
  const r = refs();
  if (r.title) r.title.textContent = tr("detailTitle");
  if (r.scoreLabel) r.scoreLabel.textContent = tr("detailScore");
  if (r.previewLabel) r.previewLabel.textContent = tr("detailPreview");
  if (r.reasonLabel) r.reasonLabel.textContent = tr("detailReason");
  if (r.closeBtn) r.closeBtn.setAttribute("aria-label", tr("detailCloseAria"));
  if (r.overlay) r.overlay.setAttribute("aria-label", tr("detailCloseAria"));
  if (currentItem) renderContent(currentItem);
}

function renderContent(item) {
  const r = refs();
  currentItem = item;
  if (r.song) r.song.textContent = item.title || "—";
  if (r.artist) r.artist.textContent = item.artist || "—";
  if (r.scoreVal) r.scoreVal.textContent = formatPercent(item.score, 0);
  if (r.previewVal) r.previewVal.textContent = item.preview_url
    ? tr("detailPreviewAvailable")
    : tr("detailPreviewUnavailable");
  if (r.reasonText) {
    const lyricSummary = item.lyric_signals?.summary ? `\n\n${item.lyric_signals.summary}` : "";
    r.reasonText.textContent = `${item.why || tr("whyFallback")}${lyricSummary}`;
  }
  if (r.link) {
    r.link.textContent = tr("openSpotify");
    if (item.spotify_url) {
      r.link.href = item.spotify_url;
      r.link.style.display = "inline-flex";
    } else {
      r.link.removeAttribute("href");
      r.link.style.display = "none";
    }
  }
}

export function openModal(item) {
  const r = refs();
  if (!r.modal || !item) return;
  renderContent(item);
  r.modal.classList.add("is-open");
  r.modal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
}

export function closeModal() {
  const r = refs();
  if (!r.modal) return;
  r.modal.classList.remove("is-open");
  r.modal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
}
