import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { useI18n } from "@/lib/i18n"

function object(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

export function DiagnosticsPanel({ qualityNotes }: { qualityNotes: Record<string, unknown> }) {
  const { t } = useI18n()
  const stageMs = object(qualityNotes.stage_ms)
  const cacheHits = object(qualityNotes.cache_hits)
  const agentic = object(qualityNotes.agentic)
  const tools = Array.isArray(agentic.tools_called) ? agentic.tools_called : []
  const trace = Array.isArray(agentic.trace) ? agentic.trace : []
  const rows = ([
    [t("stageMs"), stageMs], [t("llmUsage"), { profiler: qualityNotes.llm_profiler_used, ranker: qualityNotes.llm_ranker_used, presenter: qualityNotes.llm_presenter_used, agent_loop: qualityNotes.agent_loop_enabled }], [t("agenticMode"), `${agentic.mode_requested ?? "auto"} → ${agentic.mode_effective ?? "linear"}`], [t("agenticFallback"), agentic.fallback_reason], [t("cacheHits"), cacheHits], [t("agenticIterations"), agentic.iterations], [t("agenticTools"), tools], [t("agenticTrace"), trace], [t("refinedFrom"), qualityNotes.refined_from],
  ] as Array<[string, unknown]>).filter(([, value]) => value !== undefined && value !== null && value !== "" && (!Array.isArray(value) || value.length) && (typeof value !== "object" || Array.isArray(value) || Object.keys(value as Record<string, unknown>).length))
  if (!rows.length) return null
  return <Collapsible className="diagnostics p-3"><CollapsibleTrigger className="min-h-11 w-full text-left text-sm font-medium">{t("behindScenes")}</CollapsibleTrigger><CollapsibleContent className="pt-3"><dl className="grid gap-2 text-sm">{rows.map(([label, value]) => <div key={label} className="grid gap-1 sm:grid-cols-[10rem_1fr]"><dt className="font-medium">{label}</dt><dd className="text-muted-foreground">{typeof value === "string" || typeof value === "number" ? String(value) : JSON.stringify(value)}</dd></div>)}</dl></CollapsibleContent></Collapsible>
}