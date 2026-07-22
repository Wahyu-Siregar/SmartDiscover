import { fireEvent, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it } from "vitest"

import { I18nProvider, useI18n } from "./i18n"

function Probe() {
  const { setLanguage, t } = useI18n()
  return <button onClick={() => setLanguage("en")}>{t("heroTitle")}</button>
}

afterEach(() => localStorage.clear())

describe("I18nProvider", () => {
  it("switches language, document metadata, and saved preference", () => {
    render(
      <I18nProvider>
        <Probe />
      </I18nProvider>,
    )

    const button = screen.getByRole("button", {
      name: "Temukan musik yang cocok dengan suasanamu.",
    })
    fireEvent.click(button)

    expect(screen.getByRole("button", { name: "Find music that fits your moment." })).toBeInTheDocument()
    expect(document.documentElement.lang).toBe("en")
    expect(localStorage.smartdiscover_lang).toBe("en")
  })
})
