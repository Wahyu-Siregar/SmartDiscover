import { trackIdFromUrl } from "@/lib/format"

type PlaylistProfile = { activity?: unknown, genre?: unknown }
type TrackLike = { track_id?: unknown, spotify_url?: unknown }

function titleCase(value: unknown) {
  if (typeof value !== "string") return ""
  return value.replace(/[_-]+/g, " ").trim().split(/\s+/).filter(Boolean).map((word) => word[0].toUpperCase() + word.slice(1)).join(" ")
}

export function buildPlaylistTitle(profile: PlaylistProfile, sourceText: string, date = new Date()) {
  const activity = profile.activity === "listening" ? "" : titleCase(profile.activity)
  const genre = Array.isArray(profile.genre) ? titleCase(profile.genre[0]) : ""
  const prompt = sourceText.replace(/\s+/g, " ").trim().slice(0, 24)
  return `SmartDiscover - ${activity || genre || prompt || "Personal Mix"} - ${date.toISOString().slice(0, 10)}`
}

export function buildPlaylistDescription(profile: PlaylistProfile, sourceText: string) {
  const activity = titleCase(profile.activity) || "Listening"
  const prompt = sourceText.replace(/\s+/g, " ").trim().slice(0, 80)
  return prompt ? `SmartDiscover auto playlist for ${activity}. Prompt: ${prompt}` : `SmartDiscover auto playlist for ${activity}.`
}

export function playlistTrackIds(tracks: TrackLike[]) {
  return tracks.map((track) => typeof track.track_id === "string" && track.track_id || trackIdFromUrl(typeof track.spotify_url === "string" ? track.spotify_url : "")).filter((trackId): trackId is string => Boolean(trackId))
}