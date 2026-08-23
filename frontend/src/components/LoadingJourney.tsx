import { useEffect, useState } from "react"
import { useI18n, type MessageKey } from "@/lib/i18n"
import { SignalLine } from "./SignalLine"

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
    <section aria-label={t("pipelineTitle")} className="loading mx-auto w-full max-w-[800px] px-4 py-8">
      <p role="status" aria-live="polite" className="loading-status">
        {t("cinematicLoading")} — <strong>{t(stageKeys[stage])}</strong>
      </p>
      <SignalLine mode="progress" stage={stage} stageCount={stageKeys.length} />
      <ol className="loading-stages">
        {stageKeys.map((key, index) => (
          <li key={key} aria-current={index === stage ? "step" : undefined} className={index < stage ? "signal-done" : ""}>
            <span aria-hidden="true" className="loading-stage-idx">{String(index + 1).padStart(2, "0")}</span>
            <span className="sr-only">{stageNames[index]}: </span>{t(key)}
          </li>
        ))}
      </ol>
    </section>
  )
}
