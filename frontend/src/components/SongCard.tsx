import { motion } from "motion/react"
import { Pause, Play } from "lucide-react"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { formatDuration } from "@/lib/format"
import { useI18n } from "@/lib/i18n"
import type { RecommendationItem } from "@/types/recommendation"
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
    <motion.article variants={cardVariants} className="result-card" aria-label={`${track.rank}. ${track.title}`}>
      <Card>
        <CardHeader>
          <p className="result-rank">{String(track.rank).padStart(2, "0")}</p>
          <CardTitle className="font-display text-xl">{track.title}</CardTitle>
          <p className="text-muted-foreground">{track.artist}</p>
        </CardHeader>
        <CardContent className="grid gap-3"><p>{track.why || t("whyFallback")}</p>
          <Collapsible>
            <CollapsibleTrigger asChild><Button variant="ghost" className="justify-start px-0">{t("trackDetails")}</Button></CollapsibleTrigger>
            <CollapsibleContent className="grid gap-1 border-l border-border pl-3 text-sm text-muted-foreground">
              {value(audio.energy) && <span>{t("audioEnergy")}: {value(audio.energy)}</span>}
              {value(audio.valence) && <span>{t("audioMood")}: {value(audio.valence)}</span>}
              {value(audio.tempo) && <span>{t("audioTempo")}: {value(audio.tempo)}</span>}
              {lyric && <span>{t("lyricSignal")}: {lyric}</span>}
              {!Object.keys(audio).length && !lyric && <span>{t("noAudioDetails")}</span>}
            </CollapsibleContent>
          </Collapsible>
          {unavailable && <p role="status" className="text-sm text-muted-foreground">{t("previewAutoplayError")}</p>}
        </CardContent>
        <CardFooter className="flex flex-wrap gap-2">
          <Button disabled={!canPreview} onClick={onPreview} aria-label={canPreview ? active ? t("previewAriaPause") : t("previewAriaPlay") : t("previewAriaUnavailable")}>
            {active ? <Pause /> : <Play />}{active ? `${t("previewPause")} ${formatDuration(elapsed)}` : canPreview ? t("previewPlay") : t("previewNoPreview")}
          </Button>
          <Button variant="outline" asChild><a href={track.spotify_url} target="_blank" rel="noreferrer">{t("openSpotify")}</a></Button>
          <TrackDetailDialog track={track} />
        </CardFooter>
      </Card>
    </motion.article>
  )
}
