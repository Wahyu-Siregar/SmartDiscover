import { renderHook, waitFor } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { authStatus } from "@/lib/api"
import { useSpotifySession } from "./useSpotifySession"

vi.mock("@/lib/api", () => ({ authStatus: vi.fn() }))

describe("useSpotifySession", () => {
  afterEach(() => {
    vi.clearAllMocks()
    window.history.replaceState({}, "", "/")
  })

  it("loads the cookie-backed session and removes a legacy token query parameter", async () => {
    vi.mocked(authStatus).mockResolvedValue({ connected: true, expires_at: 12345 })
    window.history.replaceState({}, "", "/?token=legacy&tab=results")

    const { result } = renderHook(() => useSpotifySession())

    await waitFor(() => expect(result.current).toMatchObject({ connected: true, expiresAt: 12345 }))
    expect(authStatus).toHaveBeenCalledOnce()
    expect(window.location.search).toBe("?tab=results")
  })

  it("maps a failed status request to disconnected", async () => {
    vi.mocked(authStatus).mockRejectedValue(new Error("offline"))

    const { result } = renderHook(() => useSpotifySession())

    await waitFor(() => expect(result.current).toMatchObject({ connected: false, expiresAt: 0 }))
  })
})
