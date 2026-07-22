import { act, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { I18nProvider } from "@/lib/i18n"
import { LoadingJourney } from "./LoadingJourney"

describe("LoadingJourney", () => {
  afterEach(() => vi.useRealTimers())

  it("announces four localized stages and advances with one timer", () => {
    vi.useFakeTimers()
    render(<I18nProvider><LoadingJourney /></I18nProvider>)

    expect(screen.getByRole("status")).toHaveTextContent("Memahami suasana")
    expect(screen.getByRole("list").tagName).toBe("OL")

    act(() => vi.advanceTimersByTime(1200))
    expect(screen.getByRole("status")).toHaveTextContent("Mencari lagu")

    act(() => vi.advanceTimersByTime(4800))
    expect(screen.getByRole("status")).toHaveTextContent("Menyiapkan hasil")
  })
})