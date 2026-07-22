import { cleanup, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it, vi } from "vitest"
import { I18nProvider } from "@/lib/i18n"
import type { RecommendationItem } from "@/types/recommendation"
import { SongCard } from "./SongCard"

const track: RecommendationItem = {
  rank: 1, title: "First Song", artist: "Artist One", track_id: "one", spotify_url: "https://open.spotify.com/track/one",
  preview_url: "", why: "First reason", score: 0.91, audio_features: { energy: 0.2 },
}

describe("SongCard", () => {
  afterEach(cleanup)

  it("keeps secondary audio metadata collapsed and disables an unavailable preview", () => {
    render(<I18nProvider><SongCard track={track} onPreview={vi.fn()} active={false} elapsed={0} unavailable={false} /></I18nProvider>)
    expect(screen.getByRole("button", { name: /preview tidak tersedia/i })).toBeDisabled()
    expect(screen.queryByText(/energy/i)).not.toBeInTheDocument()
  })

  it("opens accessible track details", async () => {
    const user = userEvent.setup()
    render(<I18nProvider><SongCard track={{ ...track, preview_url: "https://example.test/one.mp3", lyric_signals: { summary: "gentle imagery" } }} onPreview={vi.fn()} active={false} elapsed={0} unavailable={false} /></I18nProvider>)
    await user.click(screen.getByRole("button", { name: /^detail$/i }))
    expect(screen.getByRole("dialog")).toHaveTextContent("91%")
    expect(screen.getByRole("dialog")).toHaveTextContent(/tersedia/i)
    expect(screen.getByRole("dialog")).toHaveTextContent("First reason")
    expect(screen.getByRole("dialog")).toHaveTextContent("gentle imagery")
    expect(screen.getByRole("link", { name: "Buka di Spotify" })).toBeInTheDocument()
  })
})
