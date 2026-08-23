import { Alert, AlertDescription } from "@/components/ui/alert"
import { useI18n } from "@/lib/i18n"

const warningKeys = {
  demo_catalog: "demoCatalogNotice",
  basic_matching: "basicMatchingNotice",
  low_profile_confidence: "qualityLowConfidence",
  candidate_pool_small: "qualitySmallPool",
  low_average_score: "qualityLowScore",
} as const

export function QualityAlerts({ qualityNotes, spotifyStatus }: { qualityNotes: Record<string, unknown>, spotifyStatus?: string }) {
  const { t } = useI18n()
  const warnings = Array.isArray(qualityNotes.quality_warnings) ? qualityNotes.quality_warnings.map(String) : []
  if (spotifyStatus === "mock-mode") warnings.unshift("demo_catalog")
  if (qualityNotes.llm_enabled === false) warnings.unshift("basic_matching")
  const uniqueWarnings = [...new Set(warnings)]
  if (!uniqueWarnings.length) return null

  return <div className="quality-alerts" role="status">{uniqueWarnings.map((warning) => {
    const key = warning.split(" ")[0] as keyof typeof warningKeys
    return <Alert key={warning}><AlertDescription>{key in warningKeys ? t(warningKeys[key]) : warning}</AlertDescription></Alert>
  })}</div>
}