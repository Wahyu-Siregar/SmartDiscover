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

  it("keeps secondary metadata collapsed, scores it when disclosed, and uses 44px controls", async () => {
    const user = userEvent.setup()
    render(<I18nProvider><SongCard track={track} onPreview={vi.fn()} active={false} elapsed={0} unavailable={false} /></I18nProvider>)
    const disclosure = screen.getByRole("button", { name: /detail kecocokan/i })
    const preview = screen.getByRole("button", { name: /preview tidak tersedia/i })
    expect(preview).toBeDisabled()
    expect(disclosure).toHaveClass("min-h-11")
    expect(preview).toHaveClass("min-h-11")
    expect(screen.getByRole("link", { name: /buka di spotify/i })).toHaveClass("min-h-11")
    expect(screen.queryByText(/energy/i)).not.toBeInTheDocument()

    await user.click(disclosure)
    expect(screen.getByText(/cocok: 91%/i)).toBeInTheDocument()
  })

  it("opens an associated accessible dialog with 44px controls", async () => {
    const user = userEvent.setup()
    render(<I18nProvider><SongCard track={{ ...track, preview_url: "https://example.test/one.mp3", lyric_signals: { summary: "gentle imagery" } }} onPreview={vi.fn()} active={false} elapsed={0} unavailable={false} /></I18nProvider>)
    const trigger = screen.getByRole("button", { name: /^detail$/i })
    expect(trigger).toHaveClass("min-h-11")
    await user.click(trigger)
    const dialog = screen.getByRole("dialog")
    expect(dialog).toHaveTextContent("91%")
    expect(dialog).toHaveTextContent(/tersedia/i)
    expect(dialog).toHaveTextContent("First reason")
    expect(dialog).toHaveTextContent("gentle imagery")
    expect(screen.getByRole("link", { name: "Buka di Spotify" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /tutup/i })).toHaveClass("min-h-11")
    expect(dialog).toHaveAttribute("aria-describedby")
  })
})
