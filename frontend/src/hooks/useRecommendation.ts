import { useCallback, useRef, useState } from "react"
import { recommend } from "@/lib/api"
import type { PromptValues } from "@/components/PromptComposer"
import type { RecommendResponse } from "@/types/recommendation"

export type ViewState = "idle" | "loading" | "success" | "error"

interface RecommendationState {
  view: ViewState
  result: RecommendResponse | null
  error: string
}

const initialState: RecommendationState = { view: "idle", result: null, error: "" }

export function useRecommendation(): RecommendationState & {
  submit: (values: PromptValues) => Promise<void>
  replaceResult: (result: RecommendResponse) => void
} {
  const [state, setState] = useState<RecommendationState>(initialState)
  const activeRequest = useRef(false)

  const submit = useCallback(async (values: PromptValues) => {
    if (activeRequest.current) return

    const text = values.text.trim()
    if (!text) {
      setState({ view: "error", result: null, error: "Intent is required." })
      return
    }

    activeRequest.current = true
    setState({ view: "loading", result: null, error: "" })
    try {
      const result = await recommend({ text, target_count: values.targetCount, agentic_mode: values.agenticMode })
      setState({ view: "success", result, error: "" })
    } catch (error) {
      setState({ view: "error", result: null, error: error instanceof Error && error.message ? error.message : "Request failed." })
    } finally {
      activeRequest.current = false
    }
  }, [])

  const replaceResult = useCallback((result: RecommendResponse) => {
    setState({ view: "success", result, error: "" })
  }, [])

  return { ...state, submit, replaceResult }
}