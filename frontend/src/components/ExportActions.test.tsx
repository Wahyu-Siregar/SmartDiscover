import { cleanup, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it, vi } from "vitest"
import { ApiError, createPlaylist } from "@/lib/api"
import { I18nProvider } from "@/lib/i18n"
import type { RecommendResponse } from "@/types/recommendation"
import { ExportActions } from "./ExportActions"

vi.mock("@/lib/api", async (importOriginal) => ({ ...(await importOriginal<typeof import("@/lib/api")>()), createPlaylist: vi.fn() }))

const result = {
  summary: {},
  intent_profile: { mood: "warm", activity: "reading", genre: ["indie"], energy: "low", language: "en", locale: "en-US", strict_locale: false, confidence: 0.8, target_audio: {}, seed_genres: [], decade: "", lyrical_intent: "", meaning_required: false },
  query_strategy: {}, quality_notes: {},
  recommendations: [{ rank: 1, title: "Song", artist: "Artist", track_id: "song-id", spotify_url: "", preview_url: "", why: "", score: 0.8 }],
} as RecommendResponse

function renderActions(connected: boolean, onDisconnected = vi.fn()) {
  return render(<I18nProvider><ExportActions result={result} sourceText="reading by the rain" connected={connected} onDisconnected={onDisconnected} /></I18nProvider>)
}

describe("ExportActions", () => {
  afterEach(() => { cleanup(); vi.clearAllMocks() })

  it("starts the OAuth flow when Spotify is disconnected", async () => {
    const user = userEvent.setup()
    const assign = vi.fn()
    vi.stubGlobal("location", { ...window.location, assign })
    renderActions(false)
    await user.click(screen.getByRole("button", { name: /hubungkan spotify/i }))
    expect(assign).toHaveBeenCalledWith("/auth/login")
  })

  it("keeps the playlist action at least 44px tall", () => {
    renderActions(true)
    expect(screen.getByRole("button", { name: /simpan sebagai playlist/i })).toHaveClass("min-h-11")
  })

  it("creates a cookie-authenticated playlist and exposes its URL", async () => {
    const user = userEvent.setup()
    vi.mocked(createPlaylist).mockResolvedValue({ url: "https://open.spotify.com/playlist/new" })
    renderActions(true)
    await user.click(screen.getByRole("button", { name: /simpan sebagai playlist/i }))
    await waitFor(() => expect(createPlaylist).toHaveBeenCalledWith(expect.objectContaining({ track_ids: ["song-id"] })))
    expect(await screen.findByRole("link", { name: /playlist created/i })).toHaveAttribute("href", "https://open.spotify.com/playlist/new")
  })

  it("disconnects only Spotify after an expired playlist session", async () => {
    const user = userEvent.setup()
    const onDisconnected = vi.fn()
    vi.mocked(createPlaylist).mockRejectedValue(new ApiError("expired", 401, null))
    renderActions(true, onDisconnected)
    await user.click(screen.getByRole("button", { name: /simpan sebagai playlist/i }))
    await waitFor(() => expect(onDisconnected).toHaveBeenCalledOnce())
    expect(screen.getByText(/spotify session expired/i)).toBeInTheDocument()
  })
})