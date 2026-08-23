import { Button } from "@/components/ui/button"
import { useI18n, type Locale } from "@/lib/i18n"

interface AppHeaderProps {
  connected?: boolean
  onSpotifyConnect?: () => void
}

const languages: Locale[] = ["id", "en"]

function BrandMark() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
      <rect x="2" y="7" width="3" height="8" rx="1.5" fill="#f2a35c" />
      <rect x="7" y="3" width="3" height="16" rx="1.5" fill="#f2a35c" />
      <rect x="12" y="5" width="3" height="12" rx="1.5" fill="#e8759d" />
      <rect x="17" y="9" width="3" height="4" rx="1.5" fill="#f2a35c" />
    </svg>
  )
}

export function AppHeader({ connected = false, onSpotifyConnect }: AppHeaderProps) {
  const { language, setLanguage, t } = useI18n()
  return <header className="app-header">
    <a className="brand" href="#prompt" aria-label="SmartDiscover"><BrandMark /><span>Smart<span className="brand-accent">Discover</span></span></a>
    <div className="header-controls">
      <div className="language-switch" aria-label="Language">{languages.map((nextLanguage) => <Button key={nextLanguage} type="button" variant="ghost" className="min-h-11 min-w-11 px-2 uppercase" aria-pressed={language === nextLanguage} onClick={() => setLanguage(nextLanguage)}>{nextLanguage}</Button>)}</div>
      <Button type="button" variant={connected ? "default" : "outline"} className="header-connect min-h-11" disabled={connected} onClick={onSpotifyConnect}>{connected ? t("spotifyConnected") : t("connectSpotify")}</Button>
    </div>
  </header>
}
