import { el } from "../utils/dom.js";
import { formatDuration } from "../utils/format.js";
import { tr } from "../i18n.js";

let activeAudio = null;
let activeButton = null;
let activeCard = null;
let activeProgress = null;
let activeElapsed = null;
let activeRaf = 0;

function clearActive() {
  if (activeRaf) { cancelAnimationFrame(activeRaf); activeRaf = 0; }
  if (activeAudio) {
    activeAudio.pause();
    activeAudio = null;
  }
  if (activeButton) {
    activeButton.setAttribute("aria-pressed", "false");
    activeButton.querySelector(".preview__label").textContent = tr("previewPlay");
  }
  if (activeCard) activeCard.classList.remove("is-preview-playing");
  if (activeProgress) activeProgress.style.width = "0%";
  if (activeElapsed) activeElapsed.textContent = "0:00";
  activeButton = null;
  activeCard = null;
  activeProgress = null;
  activeElapsed = null;
}

function tick() {
  if (!activeAudio || !activeProgress || !activeElapsed) return;
  const dur = Number.isFinite(activeAudio.duration) && activeAudio.duration > 0 ? activeAudio.duration : 30;
  const cur = Math.max(0, activeAudio.currentTime || 0);
  activeProgress.style.width = `${Math.min(100, (cur / dur) * 100)}%`;
  activeElapsed.textContent = formatDuration(cur);
  if (!activeAudio.paused && !activeAudio.ended) {
    activeRaf = requestAnimationFrame(tick);
  }
}

export function renderPreview(track, card) {
  if (!track.preview_url) {
    return el("button", {
      type: "button",
      class: "preview",
      disabled: true,
      "aria-label": tr("previewAriaUnavailable"),
    }, [
      el("span", { class: "preview__label", text: tr("previewNoPreview") }),
    ]);
  }

  const elapsed = el("span", { class: "preview-elapsed", text: "0:00" });
  const total = el("span", { text: ` / 0:30` });
  const progress = el("span", { class: "preview-progress", "aria-hidden": "true" }, [
    el("span", { class: "preview-progress__fill" }),
  ]);
  const meter = el("span", { class: "preview-meter" }, [elapsed, total]);

  const label = el("span", { class: "preview__label", text: tr("previewPlay") });
  const icon = el("span", { class: "preview__icon", "aria-hidden": "true" });

  const button = el("button", {
    type: "button",
    class: "preview",
    "aria-pressed": "false",
    "aria-label": tr("previewAriaPlay"),
    onClick: () => toggle(),
  }, [icon, label]);

  // Wrap so progress meter sits inline next to button.
  const wrap = el("span", { class: "preview-wrap", style: { display: "inline-flex", gap: "8px", alignItems: "center" } }, [
    button, progress, meter,
  ]);

  function toggle() {
    if (activeAudio && activeButton === button) {
      // pause current
      clearActive();
      return;
    }
    clearActive();

    const audio = new Audio(track.preview_url);
    audio.preload = "auto";
    audio.addEventListener("ended", clearActive);
    audio.addEventListener("error", () => {
      clearActive();
      label.textContent = tr("previewNoPreview");
      button.setAttribute("aria-label", tr("previewAriaUnavailable"));
    });
    audio.play().then(() => {
      activeAudio = audio;
      activeButton = button;
      activeCard = card;
      activeProgress = progress.querySelector(".preview-progress__fill");
      activeElapsed = elapsed;
      button.setAttribute("aria-pressed", "true");
      label.textContent = tr("previewPause");
      card?.classList.add("is-preview-playing");
      activeRaf = requestAnimationFrame(tick);
    }).catch(() => {
      clearActive();
    });
  }

  return wrap;
}

export function stopAllPreviews() {
  clearActive();
}
