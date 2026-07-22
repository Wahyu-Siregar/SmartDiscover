import { cleanup, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it, vi } from "vitest"
import { refine } from "@/lib/api"
import { I18nProvider } from "@/lib/i18n"
import type { RecommendResponse } from "@/types/recommendation"
import { RefineBar } from "./RefineBar"

vi.mock("@/lib/api", () => ({ refine: vi.fn() }))

const result = {
  summary: { intent_text: "warm reading songs", target_count: 8 },
  intent_profile: { mood: "warm", activity: "reading", genre: ["indie"], energy: "low", language: "en", locale: "en-US", strict_locale: false, confidence: 0.8, target_audio: {}, seed_genres: [], decade: "", lyrical_intent: "", meaning_required: false },
  query_strategy: {}, quality_notes: {},
  recommendations: [
    { rank: 1, title: "Direct", artist: "Artist", track_id: "direct", spotify_url: "", preview_url: "", why: "", score: 0.8 },
    { rank: 2, title: "URL", artist: "Artist", track_id: "", spotify_url: "https://open.spotify.com/track/from-url", preview_url: "", why: "", score: 0.7 },
  ],
} as RecommendResponse

function renderBar(onRefined = vi.fn()) {
  return render(<I18nProvider><RefineBar result={result} values={{ text: "source prompt", targetCount: 8, agenticMode: "agentic" }} onRefined={onRefined} /></I18nProvider>)
}

describe("RefineBar", () => {
  afterEach(cleanup)

  it("rejects refinement text shorter than three characters", async () => {
    const user = userEvent.setup()
    renderBar()
    await user.type(screen.getByRole("textbox", { name: /perbaiki rekomendasi/i }), "ok")
    await user.click(screen.getByRole("button", { name: /perbaiki/i }))
    expect(refine).not.toHaveBeenCalled()
  })

  it("keeps every refine control at least 44px tall", () => {
    renderBar()
    expect(screen.getByRole("textbox", { name: /perbaiki rekomendasi/i })).toHaveClass("min-h-11")
    expect(screen.getByRole("button", { name: /^perbaiki$/i })).toHaveClass("min-h-11")
    screen.getAllByRole("button").slice(1).forEach((button) => expect(button).toHaveClass("min-h-11"))
  })

  it("sends the full refine payload and replaces the latest result", async () => {
    const user = userEvent.setup()
    const onRefined = vi.fn()
    vi.mocked(refine).mockResolvedValue(result)
    renderBar(onRefined)
    await user.type(screen.getByRole("textbox", { name: /perbaiki rekomendasi/i }), "more energy")
    await user.click(screen.getByRole("button", { name: /perbaiki/i }))
    expect(refine).toHaveBeenCalledWith({ previous_profile: result.intent_profile, previous_track_ids: ["direct", "from-url"], refinement_text: "more energy", target_count: 8, agentic_mode: "agentic" })
    expect(onRefined).toHaveBeenCalledWith(result, "warm reading songs")
  })
})