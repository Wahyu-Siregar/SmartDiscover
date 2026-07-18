import json
import re
from pathlib import Path
from typing import Any

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
    "batak": ["batak", "toba", "mandailing", "karo", "simalungun", "pakpak"],
    "jawa": ["jawa", "javanese", "campursari", "keroncong", "dangdut koplo"],
    "minang": ["minang", "minang kabau", "minangkabau", "padang"],
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

GENRE_ALIASES: dict[str, str] = {
    "javanese": "jawa",
    "minangkabau": "minang",
    "minang kabau": "minang",
    "lofi": "lo-fi",
}

LYRIC_MEANING_CUES = (
    "tentang ",
    "bercerita",
    "makna",
    "arti lagu",
    "lirik",
    "about ",
    "meaning",
    "lyrics",
    "story",
    "perspective",
)


# Map app-level genre tags to Spotify Recommendations seed_genres (canonical).
# Only safe-known seeds; unknown tags are filtered out at runtime against
# /v1/recommendations/available-genre-seeds.
GENRE_TO_SPOTIFY_SEEDS: dict[str, list[str]] = {
    "lo-fi": ["chill", "study"],
    "ambient": ["ambient", "chill"],
    "classical": ["classical"],
    "pop": ["pop"],
    "rock": ["rock"],
    "jazz": ["jazz"],
    "indie": ["indie", "indie-pop"],
    "batak": ["world-music"],
    "jawa": ["world-music"],
    "minang": ["world-music"],
}

MOOD_TO_AUDIO: dict[str, dict[str, float]] = {
    "calm":      {"energy": 0.30, "valence": 0.45, "tempo": 85.0,  "acousticness": 0.55},
    "focus":     {"energy": 0.35, "valence": 0.50, "tempo": 95.0,  "instrumentalness": 0.55},
    "happy":     {"energy": 0.75, "valence": 0.80, "tempo": 118.0, "danceability": 0.70},
    "sad":       {"energy": 0.30, "valence": 0.20, "tempo": 80.0,  "acousticness": 0.55},
    "energetic": {"energy": 0.85, "valence": 0.65, "tempo": 135.0, "danceability": 0.70},
    "neutral":   {"energy": 0.50, "valence": 0.50, "tempo": 110.0},
}

ENERGY_OVERRIDE: dict[str, dict[str, float]] = {
    "low":    {"energy": 0.25, "tempo": 80.0},
    "medium": {"energy": 0.50, "tempo": 110.0},
    "high":   {"energy": 0.85, "tempo": 135.0},
}


def _load_keyword_config() -> tuple[
    dict[str, list[str]],
    dict[str, list[str]],
    dict[str, list[str]],
    list[str],
    dict[str, str],
]:
    config_path = Path(__file__).with_name("intent_keywords.json")
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        mood_keywords = data.get("mood_keywords")
        genre_keywords = data.get("genre_keywords")
        locale_keywords = data.get("locale_keywords")
        strict_locale_cues = data.get("strict_locale_cues")
        genre_aliases = data.get("genre_aliases")
        if (
            isinstance(mood_keywords, dict)
            and isinstance(genre_keywords, dict)
            and isinstance(locale_keywords, dict)
            and isinstance(strict_locale_cues, list)
            and isinstance(genre_aliases, dict)
        ):
            return (
                {str(k): [str(v) for v in values] for k, values in mood_keywords.items() if isinstance(values, list)},
                {str(k): [str(v) for v in values] for k, values in genre_keywords.items() if isinstance(values, list)},
                {str(k): [str(v) for v in values] for k, values in locale_keywords.items() if isinstance(values, list)},
                [str(v) for v in strict_locale_cues],
                {str(k).lower(): str(v) for k, v in genre_aliases.items()},
            )
    except Exception:
        pass

    return MOOD_KEYWORDS, GENRE_KEYWORDS, LOCALE_KEYWORDS, STRICT_LOCALE_CUES, GENRE_ALIASES


MOOD_KEYWORDS, GENRE_KEYWORDS, LOCALE_KEYWORDS, STRICT_LOCALE_CUES, GENRE_ALIASES = _load_keyword_config()


_FEW_SHOT_EXAMPLES = """Examples:

Input: "lagu batak buat malam minggu"
Output: {"mood":"neutral","activity":"listening","genre":["batak"],"energy":"medium","language":"id","locale":"indonesia","strict_locale":false,"confidence":0.85,"target_audio":{"energy":0.5,"valence":0.55,"tempo":105},"seed_genres":["world-music"]}

Input: "sad night songs to cry to"
Output: {"mood":"sad","activity":"listening","genre":["indie","pop"],"energy":"low","language":"en","locale":"","strict_locale":false,"confidence":0.9,"target_audio":{"energy":0.3,"valence":0.2,"tempo":80,"acousticness":0.6},"seed_genres":["sad","acoustic","indie"]}

Input: "high tempo workout mix"
Output: {"mood":"energetic","activity":"workout","genre":["pop","electronic"],"energy":"high","language":"en","locale":"","strict_locale":false,"confidence":0.92,"target_audio":{"energy":0.9,"valence":0.65,"tempo":140,"danceability":0.75},"seed_genres":["work-out","electronic","pop"]}

Input: "lagu nasionalisme indonesia"
Output: {"mood":"happy","activity":"listening","genre":[],"energy":"medium","language":"id","locale":"indonesia","strict_locale":true,"confidence":0.95,"target_audio":{"energy":0.6,"valence":0.7,"tempo":110},"seed_genres":[]}
"""


class ProfilerAgent:
    def __init__(self, llm: OpenRouterClient) -> None:
        self.llm = llm
        self.last_used_llm = False

    async def profile(self, text: str) -> IntentProfile:
        heuristic = self._profile_heuristic(text)

        llm_profile = await self._profile_with_llm(text)
        if llm_profile is None:
            self.last_used_llm = False
            return heuristic

        # Confidence-based retry once with lower temperature when result is unsure.
        if llm_profile.confidence < 0.4:
            retried = await self._profile_with_llm(text, temperature=0.05)
            if retried is not None and retried.confidence > llm_profile.confidence:
                llm_profile = retried

        self.last_used_llm = True
        return self._merge(heuristic, llm_profile)

    # ---- Hybrid merge -------------------------------------------------

    def _merge(self, heuristic: IntentProfile, llm: IntentProfile) -> IntentProfile:
        # Genre: heuristic Indonesia-specific findings act as floor (high precision).
        merged_genre: list[str] = []
        for g in heuristic.genre + llm.genre:
            if g and g not in merged_genre:
                merged_genre.append(g)

        # Prefer LLM mood/activity/energy when confidence is reasonable.
        prefer_llm = llm.confidence >= 0.5
        mood = llm.mood if prefer_llm and llm.mood else heuristic.mood
        activity = llm.activity if prefer_llm and llm.activity else heuristic.activity
        energy = llm.energy if prefer_llm else heuristic.energy
        language = llm.language or heuristic.language

        locale = llm.locale or heuristic.locale
        strict_locale = bool(llm.strict_locale or heuristic.strict_locale)

        # target_audio: prefer LLM (richer), but fill missing keys from heuristic table.
        target_audio = dict(llm.target_audio or {})
        heuristic_audio = self._derive_target_audio(mood, energy)
        for k, v in heuristic_audio.items():
            target_audio.setdefault(k, v)

        # seed_genres: union LLM + heuristic mapping, dedup.
        seed_genres: list[str] = []
        for s in (llm.seed_genres or []) + self._derive_seed_genres(merged_genre, mood):
            if s and s not in seed_genres:
                seed_genres.append(s)

        confidence = max(0.0, min(1.0, (llm.confidence + (0.6 if heuristic.genre else 0.4)) / 2))

        return IntentProfile(
            mood=mood,
            activity=activity,
            genre=merged_genre,
            energy=energy,
            language=language,
            locale=locale,
            strict_locale=strict_locale,
            confidence=confidence,
            target_audio=target_audio,
            seed_genres=seed_genres,
            decade=llm.decade or heuristic.decade,
            lyrical_intent=heuristic.lyrical_intent or llm.lyrical_intent,
            meaning_required=bool(heuristic.meaning_required or llm.meaning_required),
        )

    # ---- LLM path -----------------------------------------------------

    async def _profile_with_llm(self, text: str, *, temperature: float = 0.2) -> IntentProfile | None:
        if not self.llm.enabled:
            return None

        system_prompt = (
            "You are Profiler Agent for SmartDiscover. "
            "Extract user intent into strict JSON with keys: mood, activity, genre, energy, language, locale, "
            "strict_locale, confidence, target_audio, seed_genres, decade, lyrical_intent, meaning_required. "
            "Rules: genre is array of strings; energy is one of low|medium|high; "
            "meaning_required is true when the user asks about lyrical topic, story, message, or meaning; "
            "lyrical_intent must preserve the user's complete request when meaning_required is true, otherwise empty. "
            "language is id or en (dominant language of input); "
            "locale is empty or a country-like target such as 'indonesia'; "
            "strict_locale is true when user explicitly asks for national/local-only songs (e.g. nationalism). "
            "confidence is 0..1 reflecting how sure you are. "
            "target_audio is a numeric map with optional keys energy(0..1), valence(0..1), danceability(0..1), "
            "acousticness(0..1), instrumentalness(0..1), tempo(bpm). "
            "seed_genres is up to 5 Spotify-canonical genres for /v1/recommendations (e.g. pop, indie-pop, chill, "
            "study, work-out, classical, jazz, electronic, acoustic, sad, ambient, world-music). "
            "decade is empty or like '2010s'. "
            "Return JSON only.\n\n"
            + _FEW_SHOT_EXAMPLES
        )
        user_prompt = f"Input text: {text}"
        data = await self.llm.chat_json(
            system_prompt,
            user_prompt,
            max_tokens=400,
            temperature=temperature,
            json_mode=True,
        )
        if not data:
            return None

        try:
            mood = str(data.get("mood", "neutral"))
            activity = str(data.get("activity", "listening"))
            genre_value = data.get("genre", [])
            genre = self._normalize_genres([str(g) for g in genre_value]) if isinstance(genre_value, list) else []

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

            try:
                confidence = float(data.get("confidence", 0.5))
            except Exception:
                confidence = 0.5
            confidence = max(0.0, min(1.0, confidence))

            target_audio_raw = data.get("target_audio") or {}
            target_audio: dict[str, float] = {}
            if isinstance(target_audio_raw, dict):
                for k, v in target_audio_raw.items():
                    if k not in {"energy", "valence", "danceability", "acousticness", "instrumentalness", "tempo", "popularity"}:
                        continue
                    try:
                        target_audio[k] = float(v)
                    except Exception:
                        continue

            seed_raw = data.get("seed_genres") or []
            seed_genres: list[str] = []
            if isinstance(seed_raw, list):
                for s in seed_raw:
                    s_str = str(s).strip().lower()
                    if s_str and s_str not in seed_genres:
                        seed_genres.append(s_str)
            seed_genres = seed_genres[:5]

            decade = str(data.get("decade", "")).strip().lower()
            meaning_required = bool(data.get("meaning_required", False))
            lyrical_intent = text.strip() if meaning_required else ""

            return IntentProfile(
                mood=mood,
                activity=activity,
                genre=genre,
                energy=energy,
                language=language,
                locale=locale,
                strict_locale=strict_locale,
                confidence=confidence,
                target_audio=target_audio,
                seed_genres=seed_genres,
                decade=decade,
                lyrical_intent=lyrical_intent,
                meaning_required=meaning_required,
            )
        except Exception:
            return None

    # ---- Heuristic path -----------------------------------------------

    def _profile_heuristic(self, text: str) -> IntentProfile:
        lowered = text.lower()
        mood = self._infer_mood(lowered)
        activity = self._infer_activity(lowered)
        genres = self._infer_genres(lowered)
        energy = self._infer_energy(lowered)
        language = self._infer_language(text)
        locale = self._infer_locale(lowered)
        strict_locale = self._infer_strict_locale(lowered, locale)
        target_audio = self._derive_target_audio(mood, energy)
        seed_genres = self._derive_seed_genres(genres, mood)
        meaning_required = self._requires_lyric_meaning(lowered)
        return IntentProfile(
            mood=mood,
            activity=activity,
            genre=genres,
            energy=energy,
            language=language,
            locale=locale,
            strict_locale=strict_locale,
            confidence=0.55 if genres or mood != "neutral" else 0.35,
            target_audio=target_audio,
            seed_genres=seed_genres,
            decade="",
            lyrical_intent=text.strip() if meaning_required else "",
            meaning_required=meaning_required,
        )

    def _derive_target_audio(self, mood: str, energy: str) -> dict[str, float]:
        base = dict(MOOD_TO_AUDIO.get(mood, MOOD_TO_AUDIO["neutral"]))
        override = ENERGY_OVERRIDE.get(energy, {})
        # Energy override wins over mood-derived energy/tempo.
        base.update(override)
        return base

    def _derive_seed_genres(self, genres: list[str], mood: str) -> list[str]:
        out: list[str] = []
        for g in genres:
            for seed in GENRE_TO_SPOTIFY_SEEDS.get(g, []):
                if seed not in out:
                    out.append(seed)
        if not out:
            mood_to_seeds = {
                "calm": ["chill", "ambient"],
                "focus": ["study", "chill"],
                "happy": ["pop", "happy"],
                "sad": ["sad", "acoustic"],
                "energetic": ["work-out", "electronic"],
                "neutral": ["pop"],
            }
            out = mood_to_seeds.get(mood, ["pop"])
        return out[:5]

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
        return self._normalize_genres(genres)

    def _normalize_genres(self, genres: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for genre in genres:
            lowered = genre.strip().lower()
            canonical = GENRE_ALIASES.get(lowered, lowered)
            if canonical and canonical not in seen:
                seen.add(canonical)
                normalized.append(canonical)
        return normalized

    def _infer_energy(self, lowered: str) -> str:
        if any(k in lowered for k in ["tenang", "calm", "slow", "santai"]):
            return "low"
        if any(k in lowered for k in ["energik", "energetic", "boost", "cepat"]):
            return "high"
        return "medium"

    def _infer_language(self, text: str) -> str:
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

    @staticmethod
    def _requires_lyric_meaning(lowered: str) -> bool:
        return any(cue in lowered for cue in LYRIC_MEANING_CUES)
