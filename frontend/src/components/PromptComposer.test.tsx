import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { useState, type ComponentProps } from "react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { I18nProvider } from "@/lib/i18n"
import { PromptComposer, type PromptValues } from "./PromptComposer"

const values: PromptValues = { text: "", targetCount: 15, agenticMode: "auto" }

function renderComposer(overrides: Partial<ComponentProps<typeof PromptComposer>> = {}) {
  const onValuesChange = vi.fn()
  const onSubmit = vi.fn()
  const user = userEvent.setup()

  function ControlledComposer() {
    const [currentValues, setCurrentValues] = useState<PromptValues>(() => ({ ...values, ...overrides.values }))
    return <PromptComposer mode="hero" busy={false} {...overrides} values={currentValues} onValuesChange={(nextValues) => { onValuesChange(nextValues); setCurrentValues(nextValues) }} onSubmit={onSubmit} />
  }

  render(
    <I18nProvider>
      <ControlledComposer />
    </I18nProvider>,
  )

  return { onSubmit, onValuesChange, user }
}

describe("PromptComposer", () => {
  afterEach(cleanup)
  beforeEach(() => window.localStorage.removeItem("smartdiscover_lang"))

  it("submits with Enter but keeps Shift+Enter for a newline", async () => {
    const { onSubmit, user } = renderComposer({ values: { ...values, text: "lagu untuk malam" } })
    const textarea = screen.getByRole("textbox", { name: /musik seperti apa/i })

    await user.type(textarea, "{Shift>}{Enter}{/Shift}setelah")
    expect(onSubmit).not.toHaveBeenCalled()
    expect(textarea).toHaveValue("lagu untuk malam\nsetelah")

    await user.type(textarea, "{Enter}")
    expect(onSubmit).toHaveBeenCalledWith({ text: "lagu untuk malam\nsetelah", targetCount: 15, agenticMode: "auto" })
  })

  it("does not submit while Enter completes IME composition", () => {
    const { onSubmit } = renderComposer({ values: { ...values, text: "lagu malam" } })

    fireEvent.keyDown(screen.getByRole("textbox", { name: /musik seperti apa/i }), { key: "Enter", isComposing: true })

    expect(onSubmit).not.toHaveBeenCalled()
  })

  it("fills the textarea from a quick prompt", async () => {
    const { onValuesChange, user } = renderComposer()

    await user.click(screen.getByRole("button", { name: /fokus kerja/i }))

    expect(onValuesChange).toHaveBeenCalledWith(expect.objectContaining({ text: expect.any(String) }))
  })

  it("keeps advanced settings collapsed by default", () => {
    renderComposer()

    expect(screen.getByRole("button", { name: /pengaturan lanjutan/i })).toHaveAttribute("aria-expanded", "false")
    expect(screen.queryByRole("spinbutton", { name: /jumlah lagu/i })).not.toBeInTheDocument()
  })

  it("uses 15 and auto as the default advanced values", async () => {
    const { user } = renderComposer()

    await user.click(screen.getByRole("button", { name: /pengaturan lanjutan/i }))

    expect(screen.getByRole("spinbutton", { name: /jumlah lagu/i })).toHaveValue(15)
    expect(screen.getByRole("combobox", { name: /cara pencarian/i })).toHaveTextContent(/otomatis/i)
  })

  it("renders compact mode without losing the prompt value", () => {
    renderComposer({ mode: "compact", values: { ...values, text: "musik pagi yang tenang" } })

    expect(screen.getByRole("textbox", { name: /musik seperti apa/i })).toHaveValue("musik pagi yang tenang")
  })

  it("shows localized validation for a whitespace-only prompt", async () => {
    const { onSubmit, user } = renderComposer({ values: { ...values, text: "   " } })

    await user.click(screen.getByRole("button", { name: /cari rekomendasi/i }))

    expect(screen.getByText("Intent wajib diisi.")).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })
})