import re

from app.models import IntentProfile
from app.services.openrouter_client import OpenRouterClient


MOOD_KEYWORDS = {
    "calm": ["tenang", "calm", "chill", "relax", "healing"],
    "focus": ["fokus", "focus", "study", "belajar", "deep work"],
    "happy": ["senang", "happy", "fun", "ceria"],
    "sad": ["galau", "sad", "melancholy", "sedih"],
    "energetic": ["energik", "energetic", "workout", "lari", "gym"],
}

GENRE_KEYWORDS = {
    "lo-fi": ["lofi", "lo-fi"],
    "ambient": ["ambient"],
    "classical": ["classical", "klasik"],
    "pop": ["pop"],
    "rock": ["rock"],
    "jazz": ["jazz"],
    "indie": ["indie"],
}

LOCALE_KEYWORDS = {
    "indonesia": [
        "indonesia",
        "indonesian",
        "nusantara",
        "tanah air",
        "merah putih",
        "nkri",
        "warga indonesia",
        "lagu nasional indonesia",
    ]
}

STRICT_LOCALE_CUES = [
    "nasionalisme",
    "nationalism",
    "patriotik",
    "patriotic",
    "kemerdekaan",
    "independence",
    "kebangsaan",
    "national anthem",
]


class ProfilerAgent:
    def __init__(self, llm: OpenRouterClient) -> None:
        self.llm = llm
        self.last_used_llm = False

    async def profile(self, text: str) -> IntentProfile:
        llm_profile = await self._profile_with_llm(text)
        if llm_profile is not None:
            self.last_used_llm = True
            return llm_profile

        self.last_used_llm = False
        return self._profile_heuristic(text)

    def _profile_heuristic(self, text: str) -> IntentProfile:
        lowered = text.lower()
        mood = self._infer_mood(lowered)
        activity = self._infer_activity(lowered)
        genres = self._infer_genres(lowered)
        energy = self._infer_energy(lowered)
        language = self._infer_language(text)
        locale = self._infer_locale(lowered)
        strict_locale = self._infer_strict_locale(lowered, locale)
        return IntentProfile(
            mood=mood,
            activity=activity,
            genre=genres,
            energy=energy,
            language=language,
            locale=locale,
            strict_locale=strict_locale,
        )

    async def _profile_with_llm(self, text: str) -> IntentProfile | None:
        if not self.llm.enabled:
            return None

        system_prompt = (
            "You are Profiler Agent for SmartDiscover. "
            "Extract user intent into strict JSON with keys: mood, activity, genre, energy, language, locale, strict_locale. "
            "Rules: genre must be array of strings; energy must be one of low|medium|high; "
            "language must be id or en based on dominant user language; "
            "locale is empty or a country-like target such as 'indonesia'; "
            "strict_locale is true when user explicitly asks for national/local-only songs (e.g. nationalism request). "
            "Return JSON only."
        )
        user_prompt = f"Input text: {text}"
        data = await self.llm.chat_json(system_prompt, user_prompt, max_tokens=300)
        if not data:
            return None

        try:
            mood = str(data.get("mood", "neutral"))
            activity = str(data.get("activity", "listening"))
            genre_value = data.get("genre", [])
            genre = [str(g) for g in genre_value] if isinstance(genre_value, list) else []

            energy = str(data.get("energy", "medium")).lower()
            if energy not in {"low", "medium", "high"}:
                energy = "medium"

            language = str(data.get("language", "id")).lower()
            if language not in {"id", "en"}:
                language = self._infer_language(text)

            locale = str(data.get("locale", "")).strip().lower()
            if not locale:
                locale = self._infer_locale(text.lower())

            strict_locale = bool(data.get("strict_locale", False))
            if not strict_locale:
                strict_locale = self._infer_strict_locale(text.lower(), locale)

            return IntentProfile(
                mood=mood,
                activity=activity,
                genre=genre,
                energy=energy,
                language=language,
                locale=locale,
                strict_locale=strict_locale,
            )
        except Exception:
            return None

    def _infer_mood(self, lowered: str) -> str:
        for mood, keys in MOOD_KEYWORDS.items():
            if any(k in lowered for k in keys):
                return mood
        return "neutral"

    def _infer_activity(self, lowered: str) -> str:
        if "belajar" in lowered or "study" in lowered:
            return "studying"
        if "kerja" in lowered or "work" in lowered:
            return "working"
        if "lari" in lowered or "run" in lowered:
            return "running"
        if "tidur" in lowered or "sleep" in lowered:
            return "sleeping"
        return "listening"

    def _infer_genres(self, lowered: str) -> list[str]:
        genres: list[str] = []
        for genre, keys in GENRE_KEYWORDS.items():
            if any(k in lowered for k in keys):
                genres.append(genre)
        return genres

    def _infer_energy(self, lowered: str) -> str:
        if any(k in lowered for k in ["tenang", "calm", "slow", "santai"]):
            return "low"
        if any(k in lowered for k in ["energik", "energetic", "boost", "cepat"]):
            return "high"
        return "medium"

    def _infer_language(self, text: str) -> str:
        # Very light heuristic for Bahasa dominance.
        if re.search(r"\b(aku|yang|buat|dan|lagu|tenang|fokus)\b", text.lower()):
            return "id"
        return "en"

    def _infer_locale(self, lowered: str) -> str:
        for locale, keys in LOCALE_KEYWORDS.items():
            if any(k in lowered for k in keys):
                return locale
        return ""

    def _infer_strict_locale(self, lowered: str, locale: str) -> bool:
        if not locale:
            return False
        return any(cue in lowered for cue in STRICT_LOCALE_CUES)
