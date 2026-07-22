import { useEffect, useState } from "react"
import { useI18n, type MessageKey } from "@/lib/i18n"

const stageKeys: MessageKey[] = ["stageProfiler", "stageSearch", "stageRanker", "stagePresenter"]
const stageNames = ["profiler", "search", "ranker", "presenter"]
const STEP_MS = 1200

export function LoadingJourney() {
  const { t } = useI18n()
  const [stage, setStage] = useState(0)

  useEffect(() => {
    const timer = window.setInterval(() => {
      setStage((current) => {
        if (current === stageKeys.length - 1) {
          window.clearInterval(timer)
          return current
        }
        return current + 1
      })
    }, STEP_MS)

    return () => window.clearInterval(timer)
  }, [])

  return (
    <section aria-label={t("pipelineTitle")} className="mx-auto w-full max-w-[760px] px-4 py-8">
      <p role="status" aria-live="polite" className="mb-4 text-sm text-muted-foreground">
        {t("cinematicLoading")} {t(stageKeys[stage])}
      </p>
      <ol className="grid gap-2 sm:grid-cols-4">
        {stageKeys.map((key, index) => (
          <li key={key} aria-current={index === stage ? "step" : undefined} className="rounded-lg border border-border bg-card px-3 py-2 text-sm">
            <span aria-hidden="true" className="mr-2 text-primary">{index + 1}</span>
            <span className="sr-only">{stageNames[index]}: </span>{t(key)}
          </li>
        ))}
      </ol>
    </section>
  )
}