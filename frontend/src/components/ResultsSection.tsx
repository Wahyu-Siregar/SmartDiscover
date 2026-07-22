import { motion, useReducedMotion } from "motion/react"
import { useAudioPreview } from "@/hooks/useAudioPreview"
import { useI18n } from "@/lib/i18n"
import type { RecommendResponse } from "@/types/recommendation"
import type { PromptValues } from "./PromptComposer"
import { DiagnosticsPanel } from "./DiagnosticsPanel"
import { ExportActions } from "./ExportActions"
import { IntentSummary } from "./IntentSummary"
import { QualityAlerts } from "./QualityAlerts"
import { RefineBar } from "./RefineBar"
import { SongCard } from "./SongCard"

const listVariants = { hidden: {}, visible: { transition: { staggerChildren: 0.08 } } }

interface ResultsSectionProps {
  result: RecommendResponse
  values?: PromptValues
  sourceText?: string
  spotifyConnected?: boolean
  onSpotifyDisconnected?: () => void
  onRefined?: (result: RecommendResponse, sourceText: string) => void
}

export function ResultsSection({ result, values = { text: "", targetCount: 15, agenticMode: "auto" }, sourceText = "", spotifyConnected = false, onSpotifyDisconnected = () => {}, onRefined = () => {} }: ResultsSectionProps) {
  const { t } = useI18n()
  const reducedMotion = useReducedMotion()
  const audio = useAudioPreview(result)
  const spotifyStatus = typeof result.quality_notes.spotify_status === "string" ? result.quality_notes.spotify_status : undefined

  return <section className="result-section mx-auto w-full max-w-[760px] px-4 pb-12" aria-labelledby="results-title">
    <IntentSummary result={result} />
    <div className="result-actions">
      <RefineBar result={result} values={values} onRefined={onRefined} />
      <ExportActions result={result} sourceText={sourceText} connected={spotifyConnected} onDisconnected={onSpotifyDisconnected} />
    </div>
    <QualityAlerts qualityNotes={result.quality_notes} spotifyStatus={spotifyStatus} />
    <h2 id="results-title" className="font-display text-3xl">{t("resultsTitle")}</h2>
    {!result.recommendations.length ? <p className="mt-3 text-muted-foreground">{t("emptyNoRecommendation")}</p> : <motion.div className="mt-4 grid gap-4" variants={listVariants} initial={reducedMotion ? false : "hidden"} animate="visible">{result.recommendations.map((track) => <SongCard key={track.track_id} track={track} active={audio.activeTrackId === track.track_id} elapsed={audio.elapsed} unavailable={audio.unavailableTrackId === track.track_id} onPreview={() => { void audio.toggle(track.track_id, track.preview_url) }} />)}</motion.div>}
    <DiagnosticsPanel qualityNotes={result.quality_notes} />
  </section>
}