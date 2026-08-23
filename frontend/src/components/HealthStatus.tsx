import { Activity } from "lucide-react"
import { useI18n } from "@/lib/i18n"

export function HealthStatus() {
  const { t } = useI18n()

  return (
    <p className="health-status flex items-center gap-2 text-sm text-muted-foreground" aria-live="polite">
      <Activity aria-hidden="true" className="size-4 text-emerald-500" />
      {t("llmChecking")}
    </p>
  )
}