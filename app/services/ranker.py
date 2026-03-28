from app.models import IntentProfile, TrackCandidate
from app.services.openrouter_client import OpenRouterClient


class RankerAgent:
    def __init__(self, llm: OpenRouterClient) -> None:
        self.llm = llm
        self.last_used_llm = False

    async def rank(self, profile: IntentProfile, candidates: list[TrackCandidate], top_k: int) -> list[TrackCandidate]:
        deduped = self._dedupe(candidates)
        llm_ranked = await self._rank_with_llm(profile, deduped, top_k)
        if llm_ranked is not None:
            self.last_used_llm = True
            return llm_ranked

        self.last_used_llm = False
        scored = [self._score(profile, c) for c in deduped]
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    async def _rank_with_llm(
        self,
        profile: IntentProfile,
        candidates: list[TrackCandidate],
        top_k: int,
    ) -> list[TrackCandidate] | None:
        if not self.llm.enabled or not candidates:
            return None

        rows = []
        for idx, c in enumerate(candidates, start=1):
            rows.append(
                {
                    "idx": idx,
                    "title": c.title,
                    "artist": c.artist,
                    "popularity": c.popularity,
                }
            )

        system_prompt = (
            "You are Filter and Ranker Agent for music recommendations. "
            "Rank candidates by fit to intent profile. Return JSON only with key 'ranked'. "
            "Each item in ranked must include idx, score (0..1), why (short). "
            "If intent_profile has locale and strict_locale=true, strongly prioritize tracks matching that locale and avoid cross-country drift. "
            "Keep only the best items up to top_k."
        )
        user_prompt = (
            f"intent_profile={profile.model_dump()}\n"
            f"top_k={top_k}\n"
            f"candidates={rows}"
        )
        data = await self.llm.chat_json(system_prompt, user_prompt, max_tokens=1200)
        if not data or not isinstance(data.get("ranked"), list):
            return None

        idx_map = {i + 1: c for i, c in enumerate(candidates)}
        output: list[TrackCandidate] = []
        used: set[int] = set()
        for item in data["ranked"]:
            try:
                idx = int(item.get("idx"))
                if idx in used or idx not in idx_map:
                    continue
                used.add(idx)

                base = idx_map[idx]
                score = float(item.get("score", 0.0))
                base.score = round(max(0.0, min(1.0, score)), 4)
                base.why = str(item.get("why", "")).strip()
                output.append(base)
                if len(output) >= top_k:
                    break
            except Exception:
                continue

        return output if output else None

    def _dedupe(self, candidates: list[TrackCandidate]) -> list[TrackCandidate]:
        seen: set[str] = set()
        output: list[TrackCandidate] = []
        for c in candidates:
            key = f"{c.title.lower()}::{c.artist.lower()}"
            if key in seen:
                continue
            seen.add(key)
            output.append(c)
        return output

    def _score(self, profile: IntentProfile, candidate: TrackCandidate) -> TrackCandidate:
        text = f"{candidate.title} {candidate.artist}".lower()

        relevance = 0.25
        if profile.mood in text:
            relevance += 0.35
        if profile.activity in text:
            relevance += 0.25

        mood_energy_fit = 0.15
        if profile.energy == "low" and any(k in text for k in ["quiet", "soft", "calm", "slow"]):
            mood_energy_fit += 0.5
        if profile.energy == "high" and any(k in text for k in ["run", "fast", "boost", "pulse"]):
            mood_energy_fit += 0.5

        popularity = candidate.popularity / 100

        # Tiny diversity proxy from word uniqueness in title.
        diversity_bonus = min(1.0, len(set(candidate.title.lower().split())) / 5)

        locale_bonus = 0.0
        if profile.locale == "indonesia":
            locale_terms = ["indonesia", "indonesian", "nusantara", "tanah air", "merah putih", "garuda"]
            locale_match = any(term in text for term in locale_terms)
            if locale_match:
                locale_bonus = 0.20 if profile.strict_locale else 0.10
            elif profile.strict_locale:
                locale_bonus = -0.20

        score = (
            (relevance * 0.50)
            + (mood_energy_fit * 0.25)
            + (popularity * 0.15)
            + (diversity_bonus * 0.10)
            + locale_bonus
        )
        candidate.score = round(score, 4)
        return candidate
