import { afterEach, describe, expect, it, vi } from "vitest"

import { ApiError, recommend } from "./api"

afterEach(() => vi.unstubAllGlobals())

describe("recommend", () => {
  it("posts JSON to the recommend endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ recommendations: [] }), {
        headers: { "content-type": "application/json" },
      }),
    )
    vi.stubGlobal("fetch", fetchMock)

    await recommend({ text: "calm songs for reading" })

    expect(fetchMock).toHaveBeenCalledWith("/recommend", {
      method: "POST",
      body: JSON.stringify({ text: "calm songs for reading" }),
      headers: { "Content-Type": "application/json" },
    })
  })

  it("converts JSON details into a status-bearing ApiError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Intent is required" }), {
          status: 422,
          headers: { "content-type": "application/json" },
        }),
      ),
    )

    const error = await recommend({ text: "hi" }).catch((caught) => caught)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({
      message: "Intent is required",
      status: 422,
      data: { detail: "Intent is required" },
    })
  })
})
