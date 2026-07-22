export function trackIdFromUrl(url: string) {
  try {
    const [, trackId] = new URL(url).pathname.match(/^\/track\/([^/]+)$/) ?? []
    return trackId ?? ""
  } catch {
    return ""
  }
}

export function formatPercent(value: number, digits = 0) {
  return `${(value * 100).toFixed(digits)}%`
}

export function formatDuration(seconds: number) {
  const total = Math.max(0, Math.round(seconds))
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`
}
