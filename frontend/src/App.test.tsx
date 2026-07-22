import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import App from "./App"

describe("App", () => {
  it("renders the cinematic prompt hero", () => {
    render(<App />)
    expect(screen.getByRole("main", { name: /smartdiscover/i })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: /temukan musik/i })).toBeInTheDocument()
  })
})