import { useState, type KeyboardEvent } from "react"
import { motion, useReducedMotion } from "motion/react"
import { ChevronDown, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { useI18n } from "@/lib/i18n"
import type { AgenticMode } from "@/types/recommendation"
import { HealthStatus } from "./HealthStatus"

export interface PromptValues {
  text: string
  targetCount: number
  agenticMode: AgenticMode
}

export interface PromptComposerProps {
  mode: "hero" | "compact"
  busy: boolean
  values: PromptValues
  onValuesChange: (values: PromptValues) => void
  onSubmit: (values: PromptValues) => void
}

export function PromptComposer({ mode, busy, values, onValuesChange, onSubmit }: PromptComposerProps) {
  const { language, t } = useI18n()
  const reducedMotion = useReducedMotion()
  const [error, setError] = useState<string | null>(null)
  const quickPrompts = language === "id"
    ? [
        { label: t("chipFocus"), text: "Musik fokus untuk bekerja tanpa distraksi" },
        { label: t("chipRain"), text: "Lagu hangat untuk menemani hujan malam" },
        { label: t("chipWorkout"), text: "Musik energik untuk sesi workout" },
      ]
    : [
        { label: t("chipFocus"), text: "Focused music for working without distractions" },
        { label: t("chipRain"), text: "Warm music for a rainy night" },
        { label: t("chipWorkout"), text: "Energetic music for a workout session" },
      ]

  function submit() {
    const text = values.text.trim()
    if (!text) {
      setError(t("intentRequired"))
      return
    }
    setError(null)
    onSubmit({ ...values, text })
  }

  function handleEnter(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) return
    event.preventDefault()
    submit()
  }

  return (
    <motion.div id="prompt" layoutId="prompt-composer" transition={reducedMotion ? { duration: 0 } : { duration: 0.4 }} className={`prompt-composer prompt-composer--${mode}`}>
      <form onSubmit={(event) => { event.preventDefault(); submit() }} className="space-y-5" noValidate>
        {mode === "hero" && (
          <div className="space-y-3">
            <p className="eyebrow">{t("heroKicker")}</p>
            <h1>{t("heroTitle")}</h1>
            <p className="prompt-subtitle">{t("subtitle")}</p>
          </div>
        )}

        <div className="space-y-2">
          <Label htmlFor="music-intent">{t("intentLabel")}</Label>
          <Textarea id="music-intent" value={values.text} onChange={(event) => { setError(null); onValuesChange({ ...values, text: event.target.value }) }} onKeyDown={handleEnter} placeholder={t("intentPlaceholder")} aria-invalid={Boolean(error)} aria-describedby={error ? "intent-error" : undefined} disabled={busy} className="min-h-28 resize-y" />
          {error && <p id="intent-error" role="alert" className="text-sm text-destructive">{error}</p>}
        </div>

        {mode === "hero" && (
          <div className="space-y-2">
            <p className="text-sm font-medium">{t("quickPromptLabel")}</p>
            <div className="quick-prompts">
              {quickPrompts.map((prompt) => (
                <Button key={prompt.label} type="button" variant="outline" className="min-h-11" disabled={busy} onClick={() => { setError(null); onValuesChange({ ...values, text: prompt.text }) }}>
                  {prompt.label}
                </Button>
              ))}
            </div>
          </div>
        )}

        <Collapsible className="advanced-settings">
          <CollapsibleTrigger asChild>
            <Button type="button" variant="ghost" className="min-h-11 w-full justify-between px-0">
              {t("advancedSettings")}
              <ChevronDown aria-hidden="true" className="size-4" />
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="advanced-content">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="target-count">{t("targetCountLabel")}</Label>
                <Input id="target-count" type="number" min="1" max="50" value={values.targetCount} onChange={(event) => onValuesChange({ ...values, targetCount: Number(event.target.value) || 1 })} disabled={busy} className="min-h-11" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="agentic-mode">{t("agenticModeLabel")}</Label>
                <Select value={values.agenticMode} onValueChange={(agenticMode) => onValuesChange({ ...values, agenticMode: agenticMode as AgenticMode })} disabled={busy}>
                  <SelectTrigger id="agentic-mode" aria-label={t("agenticModeLabel")} className="min-h-11 w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="auto">{t("agenticAuto")}</SelectItem>
                    <SelectItem value="agentic">{t("agenticForce")}</SelectItem>
                    <SelectItem value="linear">{t("agenticLinear")}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <HealthStatus />
          </CollapsibleContent>
        </Collapsible>

        <Button type="submit" className="min-h-11 w-full sm:w-auto" disabled={busy}>
          <Sparkles aria-hidden="true" className="size-4" />
          {mode === "compact" ? t("compactSearch") : t("submit")}
        </Button>
      </form>
    </motion.div>
  )
}