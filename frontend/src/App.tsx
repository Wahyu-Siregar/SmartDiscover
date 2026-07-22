import { useState } from "react"
import { AppHeader } from "@/components/AppHeader"
import { PromptComposer, type PromptValues } from "@/components/PromptComposer"
import { I18nProvider } from "@/lib/i18n"

const initialValues: PromptValues = { text: "", targetCount: 15, agenticMode: "auto" }

function AppShell() {
  const [values, setValues] = useState(initialValues)

  return (
    <main aria-label="SmartDiscover" className="app-shell">
      <AppHeader />
      <section className="hero" aria-labelledby="hero-title">
        <PromptComposer mode="hero" busy={false} values={values} onValuesChange={setValues} onSubmit={setValues} />
      </section>
    </main>
  )
}

export default function App() {
  return <I18nProvider><AppShell /></I18nProvider>
}