import { Badge } from "@/components/ui/badge"
import { formatPercent } from "@/lib/format"
import { useI18n } from "@/lib/i18n"
import type { RecommendResponse } from "@/types/recommendation"

export function IntentSummary({ result }: { result: RecommendResponse }) {
  const { t } = useI18n()
  const { intent_profile: profile, summary, quality_notes: notes, recommendations } = result
  const count = summary.returned_count ?? recommendations.length
  const enhanced = Boolean(notes.llm_ranker_used || notes.llm_profiler_used)

  return (
    <section className="intent-summary" aria-label={t("intentDetected")}>
      <p className="eyebrow">{t("intentDetected")}</p>
      <p className="intent-summary__text">{summary.intent_text || "—"}</p>
      <div className="intent-summary__matrix">
        <Badge variant="outline">{t("statMood")}: {profile.mood}</Badge>
        <Badge variant="outline">{t("statActivity")}: {profile.activity}</Badge>
        <Badge variant="outline">{t("statCount")}: {count}</Badge>
        <Badge variant="outline">{t("statMode")}: {enhanced ? t("matchingEnhanced") : t("matchingBasic")}</Badge>
        <Badge variant="outline">{t("confidenceLabel")}: {formatPercent(profile.confidence)}</Badge>
      </div>
    </section>
  )
}
