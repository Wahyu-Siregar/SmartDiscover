import { $ } from "./utils/dom.js";
import { tr } from "./i18n.js";
import { getState, setState } from "./state.js";
import * as api from "./api.js";

function applyButtonStyle(btn, connected) {
  if (!btn) return;
  if (connected) {
    btn.textContent = tr("spotifyConnected");
    btn.classList.add("is-connected");
    btn.disabled = true;
  } else {
    btn.textContent = tr("connectSpotify");
    btn.classList.remove("is-connected");
    btn.disabled = false;
  }
}

export function setSpotifyConnected(connected, expiresAt = 0) {
  setState("spotifyConnected", !!connected);
  setState("spotifyExpiresAt", Number(expiresAt) || 0);
  applyButtonStyle($("spotifyLoginBtn"), !!connected);
}

export function bindSpotifyButton() {
  const btn = $("spotifyLoginBtn");
  if (!btn) return;
  btn.addEventListener("click", () => {
    if (getState("spotifyConnected")) return;
    window.location.href = "/auth/login";
  });
  applyButtonStyle(btn, getState("spotifyConnected"));
}

export async function syncOAuthStatus() {
  // Strip any legacy ?token= from the URL.
  const params = new URLSearchParams(window.location.search);
  if (params.has("token")) {
    window.history.replaceState({}, document.title, window.location.pathname);
  }
  try {
    const data = await api.authStatus();
    setSpotifyConnected(!!data.connected, data.expires_at || 0);
  } catch {
    setSpotifyConnected(false);
  }
}
