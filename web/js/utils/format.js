export function formatPercent(value, digits = 0) {
  const n = Math.max(0, Math.min(1, Number(value) || 0));
  return `${(n * 100).toFixed(digits)}%`;
}

export function formatTempo(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) return "—";
  return `${Math.round(n)} BPM`;
}

export function formatDuration(seconds) {
  const safe = Number.isFinite(seconds) && seconds > 0 ? seconds : 0;
  const m = Math.floor(safe / 60);
  const s = Math.floor(safe % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function valenceEmoji(valence) {
  const v = Number(valence);
  if (!Number.isFinite(v)) return "🎵";
  if (v < 0.3) return "😢";
  if (v < 0.55) return "😐";
  if (v < 0.75) return "😌";
  return "🤩";
}

export function trackIdFromUrl(url) {
  if (!url || typeof url !== "string") return "";
  const m = url.split("/track/")[1];
  if (!m) return "";
  return m.split("?")[0];
}

export function pad2(n) { return String(n).padStart(2, "0"); }
