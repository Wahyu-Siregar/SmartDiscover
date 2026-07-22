import type { RecommendRequest, RecommendResponse, RefineRequest } from "@/types/recommendation"

type JsonOptions = Omit<RequestInit, "headers"> & { headers?: Record<string, string> }

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly data: unknown,
  ) {
    super(message)
    this.name = "ApiError"
  }
}

function errorMessage(data: unknown, status: number) {
  if (data && typeof data === "object") {
    const detail = "detail" in data ? data.detail : "error" in data ? data.error : undefined
    if (detail) return String(detail)
  }
  return `Request failed (${status})`
}

export async function jsonFetch<T>(url: string, options: JsonOptions = {}): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  })
  let data: unknown = null
  if (response.headers.get("content-type")?.includes("application/json")) {
    try {
      data = await response.json()
    } catch {
      // Ignore invalid JSON responses to preserve the backend client's fallback error.
    }
  }
  if (!response.ok) throw new ApiError(errorMessage(data, response.status), response.status, data)
  return data as T
}

export function recommend(payload: RecommendRequest) {
  return jsonFetch<RecommendResponse>("/recommend", { method: "POST", body: JSON.stringify(payload) })
}

export function refine(payload: RefineRequest) {
  return jsonFetch<RecommendResponse>("/refine", { method: "POST", body: JSON.stringify(payload) })
}

export function authStatus() {
  return jsonFetch<Record<string, unknown>>("/auth/status", { credentials: "include" })
}

export function createPlaylist(payload: Record<string, unknown>) {
  return jsonFetch<Record<string, unknown>>("/create-playlist", {
    method: "POST",
    credentials: "include",
    body: JSON.stringify(payload),
  })
}

export function llmHealth() {
  return jsonFetch<Record<string, unknown>>("/llm/health")
}

export function spotifyHealth() {
  return jsonFetch<Record<string, unknown>>("/spotify/health")
}

