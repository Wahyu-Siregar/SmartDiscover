import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { formatPercent } from "@/lib/format"
import { useI18n } from "@/lib/i18n"
import type { RecommendationItem } from "@/types/recommendation"

function lyricSummary(track: RecommendationItem) {
  const summary = track.lyric_signals?.summary
  return typeof summary === "string" ? summary : ""
}

export function TrackDetailDialog({ track }: { track: RecommendationItem }) {
  const { t } = useI18n()
  const lyric = lyricSummary(track)

  return (
    <Dialog>
      <DialogTrigger asChild><Button variant="outline">{t("detailButton")}</Button></DialogTrigger>
      <DialogContent aria-describedby={undefined}>
        <DialogHeader><DialogTitle>{t("detailTitle")}: {track.title}</DialogTitle></DialogHeader>
        <dl className="grid gap-3 text-sm">
          <div><dt className="text-muted-foreground">{t("detailScore")}</dt><dd>{formatPercent(track.score)}</dd></div>
          <div><dt className="text-muted-foreground">{t("detailPreview")}</dt><dd>{track.preview_url ? t("detailPreviewAvailable") : t("detailPreviewUnavailable")}</dd></div>
          <div><dt className="text-muted-foreground">{t("detailReason")}</dt><dd>{track.why || t("whyFallback")}</dd></div>
          {lyric && <div><dt className="text-muted-foreground">{t("lyricSignal")}</dt><dd>{lyric}</dd></div>}
        </dl>
        <DialogDescription><a href={track.spotify_url} target="_blank" rel="noreferrer">{t("openSpotify")}</a></DialogDescription>
      </DialogContent>
    </Dialog>
  )
}
