import { act, renderHook } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { useAudioPreview } from "./useAudioPreview"

class FakeAudio {
  static events: string[] = []
  src = ""
  currentTime = 0
  onended: (() => void) | null = null
  play = vi.fn(() => {
    FakeAudio.events.push(`play:${this.src}`)
    return Promise.resolve()
  })
  pause = vi.fn(() => { FakeAudio.events.push(`pause:${this.src}`) })
}

describe("useAudioPreview", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    FakeAudio.events = []
  })

  it("pauses the active preview before playing the next one and toggles it off", async () => {
    vi.stubGlobal("Audio", FakeAudio)
    const { result } = renderHook(() => useAudioPreview("result-a"))

    await act(async () => { await result.current.toggle("a", "https://example.test/a.mp3") })
    await act(async () => { await result.current.toggle("b", "https://example.test/b.mp3") })
    expect(FakeAudio.events).toEqual(["play:https://example.test/a.mp3", "pause:https://example.test/a.mp3", "play:https://example.test/b.mp3"])
    expect(result.current.activeTrackId).toBe("b")

    await act(async () => { await result.current.toggle("b", "https://example.test/b.mp3") })
    expect(FakeAudio.events.at(-1)).toBe("pause:https://example.test/b.mp3")
    expect(result.current.activeTrackId).toBeNull()
  })
})
