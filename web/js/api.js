async function jsonFetch(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  let data = null;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) {
    try { data = await res.json(); } catch { /* ignore */ }
  }
  if (!res.ok) {
    const msg = data?.detail || data?.error || `Request failed (${res.status})`;
    const err = new Error(msg);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

export function recommend(payload) {
  return jsonFetch("/recommend", { method: "POST", body: JSON.stringify(payload) });
}

export function refine(payload) {
  return jsonFetch("/refine", { method: "POST", body: JSON.stringify(payload) });
}

export function authStatus() {
  return jsonFetch("/auth/status", { credentials: "include" });
}

export function createPlaylist(payload) {
  return jsonFetch("/create-playlist", {
    method: "POST",
    credentials: "include",
    body: JSON.stringify(payload),
  });
}

export async function promptSuggestions(q) {
  const params = new URLSearchParams({ q: q || "" });
  return jsonFetch(`/api/prompt-suggestions?${params.toString()}`);
}

export function llmHealth() {
  return jsonFetch("/llm/health");
}

export function spotifyHealth() {
  return jsonFetch("/spotify/health");
}
