import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { refine } from "@/lib/api"
import { useI18n } from "@/lib/i18n"
import { playlistTrackIds } from "@/lib/playlist"
import type { RecommendResponse } from "@/types/recommendation"
import type { PromptValues } from "./PromptComposer"

interface RefineBarProps {
  result: RecommendResponse
  values: PromptValues
  onRefined: (result: RecommendResponse, sourceText: string) => void
}

const suggestions = ["refineMore", "refineLess", "refineLessInstrumental", "refineLocalOnly"] as const

export function RefineBar({ result, values, onRefined }: RefineBarProps) {
  const { t } = useI18n()
  const [text, setText] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")

  async function submit(nextText = text) {
    const refinementText = nextText.trim()
    if (refinementText.length < 3 || busy) return
    setBusy(true)
    setError("")
    try {
      const refined = await refine({
        previous_profile: result.intent_profile,
        previous_track_ids: playlistTrackIds(result.recommendations),
        refinement_text: refinementText,
        target_count: result.summary.target_count ?? values.targetCount,
        agentic_mode: values.agenticMode,
      })
      onRefined(refined, refined.summary.intent_text || values.text)
      setText("")
    } catch (caught) {
      setError(t("refineFailed", { error: caught instanceof Error ? caught.message : "" }))
    } finally {
      setBusy(false)
    }
  }

  return <section className="mt-5 space-y-3">
    <div><p className="font-medium">{t("refineLabel")}</p><p className="text-sm text-muted-foreground">{t("refineHint")}</p></div>
    <div className="flex flex-col gap-2 sm:flex-row">
      <Input className="min-h-11" aria-label={t("refineLabel")} value={text} maxLength={200} placeholder={t("refinePlaceholder")} disabled={busy} onChange={(event) => setText(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void submit() }} />
      <Button type="button" className="min-h-11" disabled={busy} onClick={() => { void submit() }}>{busy ? t("refining") : t("refineButton")}</Button>
    </div>
    {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
    <div className="flex flex-wrap gap-2">{suggestions.map((key) => <Button key={key} type="button" variant="outline" size="sm" className="min-h-11" disabled={busy} onClick={() => { const next = t(key); setText(next); void submit(next) }}>{t(key)}</Button>)}</div>
  </section>
}