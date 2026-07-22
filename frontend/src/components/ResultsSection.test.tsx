import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it } from "vitest"
import { I18nProvider } from "@/lib/i18n"
import type { RecommendResponse } from "@/types/recommendation"
import { ResultsSection } from "./ResultsSection"

export const response: RecommendResponse = {
  summary: { intent_text: "warm songs for a rainy night", returned_count: 2 },
  intent_profile: {
    mood: "warm", activity: "reading", genre: ["indie"], energy: "low", language: "en", locale: "en-US", strict_locale: false,
    confidence: 0.88, target_audio: {}, seed_genres: [], decade: "", lyrical_intent: "reflective", meaning_required: false,
  },
  query_strategy: {},
  quality_notes: { llm_ranker_used: true, quality_warnings: ["Small candidate pool"] },
  recommendations: [
    { rank: 2, title: "Second Song", artist: "Artist Two", track_id: "two", spotify_url: "https://open.spotify.com/track/two", preview_url: "", why: "Second reason", score: 0.78, audio_features: { energy: 0.2 } },
    { rank: 1, title: "First Song", artist: "Artist One", track_id: "one", spotify_url: "https://open.spotify.com/track/one", preview_url: "https://example.test/one.mp3", why: "First reason", score: 0.91 },
  ],
}

function renderResults(result = response) {
  return render(<I18nProvider><ResultsSection result={result} /></I18nProvider>)
}

describe("ResultsSection", () => {
  afterEach(cleanup)
  it("keeps the recommendation API order", () => {
    renderResults()
    const cards = screen.getAllByRole("article")
    expect(cards[0]).toHaveTextContent("02")
    expect(cards[0]).toHaveTextContent("Second Song")
    expect(cards[0]).toHaveTextContent("Artist Two")
    expect(cards[0]).toHaveTextContent("Second reason")
    expect(cards[1]).toHaveTextContent("01")
    expect(cards[1]).toHaveTextContent("First Song")
    expect(screen.getByText("Small candidate pool")).toBeInTheDocument()
  })

  it("shows the broaden-prompt fallback for an empty response", () => {
    renderResults({ ...response, recommendations: [] })
    expect(screen.getByText(/belum ada rekomendasi/i)).toBeInTheDocument()
  })

  it("uses localized copy for the result action slot", () => {
    renderResults()
    expect(screen.getByLabelText(/perbaiki rekomendasi/i)).toBeInTheDocument()
  })
})
