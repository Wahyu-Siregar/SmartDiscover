import { motion, useReducedMotion } from "motion/react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { useAudioPreview } from "@/hooks/useAudioPreview"
import { useI18n } from "@/lib/i18n"
import type { RecommendResponse } from "@/types/recommendation"
import { IntentSummary } from "./IntentSummary"
import { SongCard } from "./SongCard"

const listVariants = { hidden: {}, visible: { transition: { staggerChildren: 0.08 } } }

export function ResultsSection({ result }: { result: RecommendResponse }) {
  const { t } = useI18n()
  const reducedMotion = useReducedMotion()
  const audio = useAudioPreview(result)
  const warnings = result.quality_notes.quality_warnings ?? []

  return (
    <section className="result-section mx-auto w-full max-w-[760px] px-4 pb-12" aria-labelledby="results-title">
      <IntentSummary result={result} />
      <div className="result-actions" aria-label={t("refineLabel")} />
      {warnings.map((warning) => <Alert key={warning} className="mb-3"><AlertDescription>{warning}</AlertDescription></Alert>)}
      <h2 id="results-title" className="font-display text-3xl">{t("resultsTitle")}</h2>
      {!result.recommendations.length ? <p className="mt-3 text-muted-foreground">{t("emptyNoRecommendation")}</p> : (
        <motion.div className="mt-4 grid gap-4" variants={listVariants} initial={reducedMotion ? false : "hidden"} animate="visible">
          {result.recommendations.map((track) => <SongCard key={track.track_id} track={track} active={audio.activeTrackId === track.track_id} elapsed={audio.elapsed} unavailable={audio.unavailableTrackId === track.track_id} onPreview={() => { void audio.toggle(track.track_id, track.preview_url) }} />)}
        </motion.div>
      )}
    </section>
  )
}
