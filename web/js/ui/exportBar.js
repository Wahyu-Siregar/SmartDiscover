import { $, el, clearChildren, setHidden } from "../utils/dom.js";
import { tr } from "../i18n.js";
import { getState } from "../state.js";
import * as api from "../api.js";
import { trackIdFromUrl } from "../utils/format.js";
import { setStatus } from "../render.js";
import { setSpotifyConnected } from "../oauth.js";

function toTitle(s) {
  if (!s || typeof s !== "string") return "";
  return s.replace(/[_-]+/g, " ").trim().split(/\s+/).map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

function buildPlaylistTitle(data, sourceText) {
  const profile = data?.intent_profile || {};
  const activity = profile.activity && profile.activity !== "listening" ? toTitle(profile.activity) : "";
  const genre = Array.isArray(profile.genre) && profile.genre.length ? toTitle(String(profile.genre[0])) : "";
  const fallback = String(sourceText || "").replace(/\s+/g, " ").trim().slice(0, 24);
  const core = activity || genre || fallback || "Personal Mix";
  const dateText = new Date().toISOString().slice(0, 10);
  return `SmartDiscover - ${core} - ${dateText}`;
}

function buildPlaylistDescription(data, sourceText) {
  const profile = data?.intent_profile || {};
  const activity = toTitle(profile.activity || "Listening");
  const mood = toTitle(profile.mood || "Neutral");
  const compact = String(sourceText || "").replace(/\s+/g, " ").trim().slice(0, 80);
  if (compact) {
    return `SmartDiscover auto playlist for ${activity} (${mood}). Prompt: ${compact}`;
  }
  return `SmartDiscover auto playlist for ${activity} (${mood}).`;
}

export function renderExportBar(data, sourceText) {
  const slot = $("exportSlot");
  if (!slot) return;
  clearChildren(slot);

  const list = data?.recommendations || [];
  if (!list.length) {
    setHidden(slot, true);
    return;
  }
  setHidden(slot, false);

  const connected = !!getState("spotifyConnected");
  const btn = el("button", {
    type: "button",
    class: "btn btn--ghost",
    text: connected ? tr("exportSave") : tr("exportLogin"),
  });

  btn.addEventListener("click", async () => {
    if (!getState("spotifyConnected")) {
      window.location.href = "/auth/login";
      return;
    }
    btn.disabled = true;
    btn.textContent = tr("exportCreating");
    try {
      const trackIds = list
        .map((r) => r.track_id || trackIdFromUrl(r.spotify_url))
        .filter(Boolean);

      const res = await api.createPlaylist({
        title: buildPlaylistTitle(data, sourceText),
        description: buildPlaylistDescription(data, sourceText),
        track_ids: trackIds,
      });

      if (res?.url) {
        btn.textContent = tr("exportCreated");
        btn.disabled = false;
        btn.replaceWith(el("a", {
          class: "btn btn--ghost",
          href: res.url,
          target: "_blank",
          rel: "noopener noreferrer",
          text: tr("exportCreated"),
        }));
        setStatus(tr("exportSuccessStatus"));
      } else {
        throw new Error(tr("genericFailedPlaylist"));
      }
    } catch (err) {
      if (err?.status === 401) {
        setSpotifyConnected(false);
        setStatus(tr("spotifyExpired"), true);
      } else {
        setStatus(tr("exportFailed", { error: err.message || "" }), true);
      }
      btn.disabled = false;
      btn.textContent = tr("exportErrorTryAgain");
    }
  });

  slot.appendChild(el("div", { class: "cluster", style: { justifyContent: "flex-end" } }, [btn]));
}
