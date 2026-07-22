import { describe, expect, it } from "vitest"

import { formatDuration, formatPercent, trackIdFromUrl } from "./format"

describe("formatting helpers", () => {
  it("extracts a Spotify track id", () => {
    expect(trackIdFromUrl("https://open.spotify.com/track/abc123?si=x")).toBe("abc123")
  })

  it("formats a decimal score as a percentage", () => {
    expect(formatPercent(0.876, 0)).toBe("88%")
  })

  it("formats duration as minutes and seconds", () => {
    expect(formatDuration(65)).toBe("1:05")
  })
})
