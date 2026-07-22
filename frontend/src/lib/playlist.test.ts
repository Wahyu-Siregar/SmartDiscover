import { describe, expect, it } from "vitest"
import { buildPlaylistTitle, playlistTrackIds } from "./playlist"

describe("playlist helpers", () => {
  it("prioritizes activity, then genre, then a capped prompt in the playlist title", () => {
    const date = new Date("2026-07-22T00:00:00.000Z")

    expect(buildPlaylistTitle({ activity: "night_run", genre: ["indie"] }, "quiet songs", date)).toBe("SmartDiscover - Night Run - 2026-07-22")
    expect(buildPlaylistTitle({ activity: "listening", genre: ["dream_pop"] }, "quiet songs", date)).toBe("SmartDiscover - Dream Pop - 2026-07-22")
    expect(buildPlaylistTitle({}, "  songs for a very long thoughtful rainy evening  ", date)).toBe("SmartDiscover - songs for a very long th - 2026-07-22")
  })

  it("uses the response ID or falls back to the Spotify track URL", () => {
    expect(playlistTrackIds([
      { track_id: "direct-id" },
      { spotify_url: "https://open.spotify.com/track/from-url?si=abc" },
      { track_id: "" },
    ])).toEqual(["direct-id", "from-url"])
  })
})
