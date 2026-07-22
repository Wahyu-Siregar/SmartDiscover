import { act, renderHook, waitFor } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { recommend } from "@/lib/api"
import type { RecommendResponse } from "@/types/recommendation"
import { useRecommendation } from "./useRecommendation"

vi.mock("@/lib/api", () => ({ recommend: vi.fn() }))

const response = {} as RecommendResponse

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((nextResolve, nextReject) => {
    resolve = nextResolve
    reject = nextReject
  })
  return { promise, resolve, reject }
}

describe("useRecommendation", () => {
  afterEach(() => vi.clearAllMocks())

  it("moves from loading to success and maps prompt values to the request", async () => {
    const request = deferred<RecommendResponse>()
    vi.mocked(recommend).mockReturnValueOnce(request.promise)
    const { result } = renderHook(() => useRecommendation())

    let submitted!: Promise<void>
    act(() => {
      submitted = result.current.submit({ text: "  lagu untuk malam  ", targetCount: 9, agenticMode: "agentic" })
    })

    expect(result.current.view).toBe("loading")
    expect(recommend).toHaveBeenCalledWith({ text: "lagu untuk malam", target_count: 9, agentic_mode: "agentic" })

    await act(async () => {
      request.resolve(response)
      await submitted
    })

    expect(result.current).toMatchObject({ view: "success", result: response, error: "" })
  })

  it("ignores a duplicate submit while a request is active", () => {
    const request = deferred<RecommendResponse>()
    vi.mocked(recommend).mockReturnValueOnce(request.promise)
    const { result } = renderHook(() => useRecommendation())

    act(() => {
      void result.current.submit({ text: "lagu pagi", targetCount: 15, agenticMode: "auto" })
      void result.current.submit({ text: "lagu pagi", targetCount: 15, agenticMode: "auto" })
    })

    expect(recommend).toHaveBeenCalledTimes(1)
  })

  it("exposes a plain request error", async () => {
    vi.mocked(recommend).mockRejectedValueOnce(new Error("Backend unavailable"))
    const { result } = renderHook(() => useRecommendation())

    await act(async () => {
      await result.current.submit({ text: "lagu pagi", targetCount: 15, agenticMode: "auto" })
    })

    await waitFor(() => expect(result.current).toMatchObject({ view: "error", error: "Backend unavailable" }))
  })
})