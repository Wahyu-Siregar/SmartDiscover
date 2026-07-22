import { useCallback, useEffect, useState } from "react"
import { authStatus } from "@/lib/api"

interface SpotifySession {
  connected: boolean
  expiresAt: number
}

const disconnected: SpotifySession = { connected: false, expiresAt: 0 }

function removeLegacyToken() {
  const url = new URL(window.location.href)
  if (!url.searchParams.has("token")) return
  url.searchParams.delete("token")
  window.history.replaceState({}, document.title, `${url.pathname}${url.search}${url.hash}`)
}

export function useSpotifySession() {
  const [session, setSession] = useState<SpotifySession>(disconnected)

  useEffect(() => {
    removeLegacyToken()
    let active = true
    void authStatus()
      .then((data) => {
        if (active) setSession({ connected: data.connected === true, expiresAt: Number(data.expires_at) || 0 })
      })
      .catch(() => { if (active) setSession(disconnected) })
    return () => { active = false }
  }, [])

  return { ...session, disconnect: useCallback(() => setSession(disconnected), []) }
}