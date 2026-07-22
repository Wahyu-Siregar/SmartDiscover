import { cleanup, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { recommend } from "@/lib/api"

vi.mock("@/lib/api", () => ({ recommend: vi.fn(), authStatus: vi.fn().mockResolvedValue({ connected: false }) }))

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((nextResolve, nextReject) => {
    resolve = nextResolve
    reject = nextReject
  })
  return { promise, resolve, reject }
}

async function renderApp() {
  const { default: App } = await import("./App")
  render(<App />)
}

const mediaListeners = new Set<(event: Event) => void>()
const mediaQuery = {
  matches: false,
  media: "(prefers-reduced-motion)",
  onchange: null,
  addListener: () => {},
  removeListener: () => {},
  addEventListener: (_: string, listener: (event: Event) => void) => mediaListeners.add(listener),
  removeEventListener: (_: string, listener: (event: Event) => void) => mediaListeners.delete(listener),
  dispatchEvent: () => false,
}

function setReducedMotion(matches: boolean) {
  mediaQuery.matches = matches
  mediaListeners.forEach((listener) => listener(new Event("change")))
}

describe("App", () => {
  const scrollIntoView = vi.fn()
  const textbox = () => screen.getByRole("textbox", { name: /musik seperti apa/i })

  beforeEach(() => {
    window.matchMedia = () => mediaQuery
    setReducedMotion(false)
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", { configurable: true, value: scrollIntoView })
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it("renders the cinematic prompt hero", async () => {
    await renderApp()
    expect(screen.getByRole("main", { name: /smartdiscover/i })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: /temukan musik/i })).toBeInTheDocument()
    expect(screen.getByRole("region", { name: /temukan musik/i })).toBeInTheDocument()
  })

  it("moves from idle to loading and renders the compact prompt", async () => {
    const request = deferred<never>()
    vi.mocked(recommend).mockReturnValueOnce(request.promise)
    const user = userEvent.setup()
    await renderApp()

    await user.type(textbox(), "lagu untuk malam")
    await user.click(screen.getByRole("button", { name: /cari rekomendasi/i }))

    expect(screen.queryByRole("heading", { name: /temukan musik/i })).not.toBeInTheDocument()
    expect(screen.getByRole("status")).toBeInTheDocument()
  })

  it("scrolls the loading journey into view when motion is allowed", async () => {
    const request = deferred<never>()
    vi.mocked(recommend).mockReturnValueOnce(request.promise)
    const user = userEvent.setup()
    await renderApp()

    await user.type(textbox(), "lagu untuk malam")
    await user.click(screen.getByRole("button", { name: /cari rekomendasi/i }))

    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: "smooth", block: "start" })
  })

  it("does not request smooth scrolling when reduced motion is enabled", async () => {
    setReducedMotion(true)
    const request = deferred<never>()
    vi.mocked(recommend).mockReturnValueOnce(request.promise)
    const user = userEvent.setup()
    await renderApp()

    await user.type(textbox(), "lagu untuk malam")
    await user.click(screen.getByRole("button", { name: /cari rekomendasi/i }))

    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: "auto", block: "start" })
  })

  it("enters error while preserving prompt values", async () => {
    vi.mocked(recommend).mockRejectedValueOnce(new Error("Backend unavailable"))
    const user = userEvent.setup()
    await renderApp()

    await user.type(textbox(), "lagu untuk malam")
    await user.click(screen.getByRole("button", { name: /cari rekomendasi/i }))

    expect(await screen.findByRole("alert")).toHaveTextContent("Backend unavailable")
    expect(textbox()).toHaveValue("lagu untuk malam")
    expect(textbox()).not.toBeDisabled()
  })
})