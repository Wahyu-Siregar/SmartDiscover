import { useState } from "react"
import { Button } from "@/components/ui/button"
import { ApiError, createPlaylist } from "@/lib/api"
import { useI18n } from "@/lib/i18n"
import { buildPlaylistDescription, buildPlaylistTitle, playlistTrackIds } from "@/lib/playlist"
import type { RecommendResponse } from "@/types/recommendation"

interface ExportActionsProps {
  result: RecommendResponse
  sourceText: string
  connected: boolean
  onDisconnected: () => void
}

export function ExportActions({ result, sourceText, connected, onDisconnected }: ExportActionsProps) {
  const { t } = useI18n()
  const [busy, setBusy] = useState(false)
  const [url, setUrl] = useState("")
  const [error, setError] = useState("")

  async function exportPlaylist() {
    if (!connected) {
      window.location.assign("/auth/login")
      return
    }
    setBusy(true)
    setError("")
    try {
      const response = await createPlaylist({
        title: buildPlaylistTitle(result.intent_profile, sourceText),
        description: buildPlaylistDescription(result.intent_profile, sourceText),
        track_ids: playlistTrackIds(result.recommendations),
      })
      if (typeof response.url !== "string" || !response.url) throw new Error(t("genericFailedPlaylist"))
      setUrl(response.url)
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        onDisconnected()
        setError(t("spotifyExpired"))
      } else {
        setError(t("exportFailed", { error: caught instanceof Error ? caught.message : "" }))
      }
    } finally {
      setBusy(false)
    }
  }

  if (!result.recommendations.length) return null
  if (url) return <a className="inline-flex min-h-11 items-center" href={url} target="_blank" rel="noreferrer">{t("exportCreated")}</a>

  return <div className="mt-5 space-y-2">
    <Button type="button" variant="outline" className="min-h-11" disabled={busy} onClick={() => { void exportPlaylist() }}>{busy ? t("exportCreating") : connected ? t("exportSave") : t("exportLogin")}</Button>
    {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
  </div>
}