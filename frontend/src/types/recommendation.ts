export type AgenticMode = "auto" | "agentic" | "linear"

export interface RecommendRequest {
  text: string
  target_count?: number
  agentic_mode?: AgenticMode
}

export interface IntentProfile {
  mood: string
  activity: string
  genre: string[]
  energy: "low" | "medium" | "high"
  language: "id" | "en"
  locale: string
  strict_locale: boolean
  confidence: number
  target_audio: Record<string, number>
  seed_genres: string[]
  decade: string
  lyrical_intent: string
  meaning_required: boolean
}

export interface RefineRequest {
  previous_profile: IntentProfile
  previous_track_ids?: string[]
  refinement_text: string
  target_count?: number
  agentic_mode?: AgenticMode
}

export interface RecommendationItem {
  rank: number
  title: string
  artist: string
  track_id: string
  spotify_url: string
  preview_url: string
  why: string
  score: number
  audio_features?: Record<string, number> | null
  lyric_signals?: Record<string, unknown> | null
}

export interface RecommendResponse {
  summary: Record<string, unknown> & {
    intent_text?: string
    target_count?: number
    returned_count?: number
  }
  intent_profile: IntentProfile
  query_strategy: Record<string, unknown>
  recommendations: RecommendationItem[]
  quality_notes: Record<string, unknown> & {
    stage_ms?: Record<string, number>
    quality_warnings?: string[]
    llm_enabled?: boolean
    llm_profiler_used?: boolean
    llm_ranker_used?: boolean
    llm_presenter_used?: boolean
    agent_loop_enabled?: boolean
    agentic?: Record<string, unknown>
  }
}
