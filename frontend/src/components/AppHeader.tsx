import logo from "@/assets/logo.svg"
import { Button } from "@/components/ui/button"
import { useI18n, type Locale } from "@/lib/i18n"

interface AppHeaderProps {
  connected?: boolean
  onSpotifyConnect?: () => void
}

const languages: Locale[] = ["id", "en"]

export function AppHeader({ connected = false, onSpotifyConnect }: AppHeaderProps) {
  const { language, setLanguage, t } = useI18n()
  return <header className="app-header">
    <a className="brand" href="#prompt" aria-label="SmartDiscover"><img src={logo} alt="" aria-hidden="true" className="size-7" /><span>SmartDiscover</span></a>
    <div className="header-controls">
      <div className="language-switch" aria-label="Language">{languages.map((nextLanguage) => <Button key={nextLanguage} type="button" variant="ghost" className="min-h-11 min-w-11 px-2 uppercase" aria-pressed={language === nextLanguage} onClick={() => setLanguage(nextLanguage)}>{nextLanguage}</Button>)}</div>
      <Button type="button" variant="outline" className="min-h-11" disabled={connected} onClick={onSpotifyConnect}>{connected ? t("spotifyConnected") : t("connectSpotify")}</Button>
    </div>
  </header>
}
