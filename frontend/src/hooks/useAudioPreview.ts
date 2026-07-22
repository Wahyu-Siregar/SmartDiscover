import { useCallback, useEffect, useRef, useState } from "react"

export function useAudioPreview(resultKey: unknown) {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const frameRef = useRef<number | null>(null)
  const attemptRef = useRef(0)
  const [activeTrackId, setActiveTrackId] = useState<string | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const [unavailableTrackId, setUnavailableTrackId] = useState<string | null>(null)

  const stop = useCallback(() => {
    attemptRef.current += 1
    if (frameRef.current != null && typeof cancelAnimationFrame === "function") cancelAnimationFrame(frameRef.current)
    frameRef.current = null
    audioRef.current?.pause()
    setActiveTrackId(null)
    setElapsed(0)
  }, [])

  useEffect(() => stop, [resultKey, stop])

  const toggle = useCallback(async (trackId: string, previewUrl: string) => {
    const audio = audioRef.current ?? (audioRef.current = new Audio())
    if (activeTrackId === trackId) {
      stop()
      return
    }

    if (activeTrackId) stop()
    audio.src = previewUrl
    audio.currentTime = 0
    setElapsed(0)
    setUnavailableTrackId(null)
    setActiveTrackId(trackId)
    const attempt = ++attemptRef.current
    const tick = () => {
      setElapsed(audio.currentTime)
      frameRef.current = requestAnimationFrame(tick)
    }

    audio.onended = stop
    try {
      await audio.play()
      if (typeof requestAnimationFrame === "function") frameRef.current = requestAnimationFrame(tick)
    } catch {
      if (attempt === attemptRef.current) {
        audio.pause()
        setActiveTrackId(null)
        setUnavailableTrackId(trackId)
      }
    }
  }, [activeTrackId, stop])

  return { activeTrackId, elapsed, unavailableTrackId, toggle }
}
