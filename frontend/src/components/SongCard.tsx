import { motion } from "motion/react"
import { Pause, Play } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { formatDuration, formatPercent } from "@/lib/format"
import { useI18n } from "@/lib/i18n"
import type { RecommendationItem } from "@/types/recommendation"
import { SignalLine } from "./SignalLine"
import { TrackDetailDialog } from "./TrackDetailDialog"

export const cardVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0 },
}

function value(value: unknown) {
  return typeof value === "number" ? value.toFixed(value <= 1 ? 2 : 0) : null
}

export function SongCard({ track, onPreview, active, elapsed, unavailable }: {
  track: RecommendationItem
  onPreview: () => void
  active: boolean
  elapsed: number
  unavailable: boolean
}) {
  const { t } = useI18n()
  const audio = track.audio_features ?? {}
  const lyric = typeof track.lyric_signals?.summary === "string" ? track.lyric_signals.summary : ""
  const canPreview = Boolean(track.preview_url) && !unavailable

  return (
    <motion.article variants={cardVariants} className="track-row" aria-label={`${track.rank}. ${track.title}`}>
      <div className="track-row__panel">
        <div className="track-row__main">
          <p className="track-row__rank">{String(track.rank).padStart(2, "0")}</p>
          <div className="track-row__body">
            <h3 className="track-row__title">{track.title}</h3>
            <p className="track-row__artist">{track.artist}</p>
            <p className="track-row__why">{track.why || t("whyFallback")}</p>
            <Collapsible className="track-row__details">
              <CollapsibleTrigger asChild><Button variant="ghost" className="track-row__details-trigger min-h-11 justify-start px-0">{t("trackDetails")}</Button></CollapsibleTrigger>
              <CollapsibleContent className="track-row__details-content">
                <span>{t("matchLabel")}: {formatPercent(track.score)}</span>
                {value(audio.energy) && <span>{t("audioEnergy")}: {value(audio.energy)}</span>}
                {value(audio.valence) && <span>{t("audioMood")}: {value(audio.valence)}</span>}
                {value(audio.tempo) && <span>{t("audioTempo")}: {value(audio.tempo)}</span>}
                {lyric && <span>{t("lyricSignal")}: {lyric}</span>}
                {!Object.keys(audio).length && !lyric && <span>{t("noAudioDetails")}</span>}
              </CollapsibleContent>
            </Collapsible>
          </div>
          <div className="track-row__side">
            <p className="track-row__score">{formatPercent(track.score)}</p>
            <SignalLine mode="mini" track={track} active={active} />
          </div>
        </div>
        {unavailable && <p role="status" className="track-row__unavailable">{t("previewAutoplayError")}</p>}
        <div className="track-row__actions">
          <Button className="min-h-11" disabled={!canPreview} onClick={onPreview} aria-label={canPreview ? active ? t("previewAriaPause") : t("previewAriaPlay") : t("previewAriaUnavailable")}>
            {active ? <Pause /> : <Play />}{active ? `${t("previewPause")} ${formatDuration(elapsed)}` : canPreview ? t("previewPlay") : t("previewNoPreview")}
          </Button>
          <Button variant="outline" className="min-h-11" asChild><a href={track.spotify_url} target="_blank" rel="noreferrer">{t("openSpotify")}</a></Button>
          <TrackDetailDialog track={track} />
        </div>
      </div>
    </motion.article>
  )
}
