import { useMemo } from "react"
import type { RecommendationItem } from "@/types/recommendation"

function hash(seed: string) {
  let h = 0
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0
  return h
}

function pattern(length: number, seed: string) {
  const h = hash(seed)
  const out: number[] = []
  for (let i = 0; i < length; i++) {
    const wave = 0.5 + 0.5 * Math.sin(i * 0.52 + (h % 7))
    const jitter = ((h >>> (i * 5)) & 15) / 16
    out.push(0.2 + 0.55 * wave + 0.25 * jitter)
  }
  return out
}

interface SignalLineProps {
  mode: "hero" | "progress" | "mini"
  stage?: number
  stageCount?: number
  active?: boolean
  track?: RecommendationItem
}

export function SignalLine({ mode, stage = 0, stageCount = 4, active = false, track }: SignalLineProps) {
  const heights = useMemo(() => {
    if (mode === "mini" && track) {
      const audio = track.audio_features ?? {}
      const energy = typeof audio.energy === "number" ? audio.energy : 0.5
      const valence = typeof audio.valence === "number" ? audio.valence : 0.5
      const lift = Math.max(0.1, Math.min(1, energy * 0.65 + valence * 0.35))
      return pattern(24, track.track_id).map((value) => Math.max(0.16, Math.min(1, value * lift)))
    }
    if (mode === "progress") return pattern(48, "progress")
    return pattern(48, "hero")
  }, [mode, track])

  const filledBars = mode === "progress" ? Math.min(heights.length, Math.round(((stage + 1) / stageCount) * heights.length)) : null

  return (
    <div className={`signal signal--${mode}${active ? " signal--playing" : ""}`} aria-hidden="true">
      {heights.map((height, index) => {
        const state = filledBars == null ? "" : index < filledBars ? " signal__on" : index === filledBars ? " signal__current" : ""
        return <span key={index} className={state} style={{ height: `${Math.round(height * 100)}%`, animationDelay: `${(index % 8) * 0.09}s` }} />
      })}
    </div>
  )
}
