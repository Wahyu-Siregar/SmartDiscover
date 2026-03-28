from app.models import IntentProfile, RecommendationItem, TrackCandidate


class PresenterAgent:
    def present(self, profile: IntentProfile, tracks: list[TrackCandidate]) -> list[RecommendationItem]:
        items: list[RecommendationItem] = []
        for idx, track in enumerate(tracks, start=1):
            reason = self._build_reason(profile, track)
            items.append(
                RecommendationItem(
                    rank=idx,
                    title=track.title,
                    artist=track.artist,
                    spotify_url=track.spotify_url,
                    preview_url=track.preview_url,
                    why=reason,
                    score=track.score,
                )
            )
        return items

    def _build_reason(self, profile: IntentProfile, track: TrackCandidate) -> str:
        if track.why.strip():
            return track.why
        locale_hint = ""
        if profile.locale:
            locale_hint = f" dengan konteks {profile.locale}" if profile.language == "id" else f" with {profile.locale} context"
        if profile.language == "id":
            return f"Cocok untuk {profile.activity} dengan nuansa {profile.mood} dan energi {profile.energy}{locale_hint}."
        return f"Good fit for {profile.activity} with a {profile.mood} mood and {profile.energy} energy{locale_hint}."
