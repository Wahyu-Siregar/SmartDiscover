import { useEffect, useRef, useState } from "react"
import { motion, useReducedMotion } from "motion/react"
import { AppHeader } from "@/components/AppHeader"
import { LoadingJourney } from "@/components/LoadingJourney"
import { PromptComposer, type PromptValues } from "@/components/PromptComposer"
import { ResultsSection } from "@/components/ResultsSection"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { useRecommendation } from "@/hooks/useRecommendation"
import { useSpotifySession } from "@/hooks/useSpotifySession"
import { spotifyHealth } from "@/lib/api"
import { I18nProvider, useI18n } from "@/lib/i18n"

const initialValues: PromptValues = { text: "", targetCount: 15, agenticMode: "auto" }

function AppShell() {
  const [values, setValues] = useState(initialValues)
  const [sourceText, setSourceText] = useState("")
  const [spotifyStatus, setSpotifyStatus] = useState("")
  const { view, error, result, submit, replaceResult } = useRecommendation()
  const spotify = useSpotifySession()
  const reducedMotion = useReducedMotion()
  const loadingRef = useRef<HTMLElement>(null)
  const { t } = useI18n()
  const idle = view === "idle"

  useEffect(() => {
    let active = true
    void spotifyHealth().then((health) => { if (active) setSpotifyStatus(health.status) }).catch(() => {})
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!idle) loadingRef.current?.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "start" })
  }, [idle, reducedMotion])

  return <main aria-label="SmartDiscover" className="app-shell">
    <AppHeader connected={spotify.connected} onSpotifyConnect={() => window.location.assign("/auth/login")} />
    <motion.section layout transition={reducedMotion ? { duration: 0 } : { duration: 0.4 }} className={idle ? "hero" : "mx-auto w-full max-w-[800px] px-4 py-6"} aria-labelledby={idle ? "hero-title" : undefined}>
      <PromptComposer mode={idle ? "hero" : "compact"} busy={view === "loading"} values={values} onValuesChange={setValues} onSubmit={(nextValues) => { setSourceText(nextValues.text); void submit(nextValues) }} />
    </motion.section>
    {!idle && <section ref={loadingRef} aria-label={t("cinematicLoading")}>
      {view === "loading" && <LoadingJourney />}
      {view === "error" && <div className="mx-auto w-full max-w-[800px] px-4 py-8"><Alert variant="destructive"><AlertTitle>{t("loadError")}</AlertTitle><AlertDescription>{error}</AlertDescription></Alert></div>}
      {view === "success" && result && <ResultsSection result={result} values={values} sourceText={sourceText} spotifyStatus={spotifyStatus} spotifyConnected={spotify.connected} onSpotifyDisconnected={spotify.disconnect} onRefined={(refined, prompt) => { setSourceText(prompt); replaceResult(refined) }} />}
    </section>}
  </main>
}

export default function App() {
  return <I18nProvider><AppShell /></I18nProvider>
}