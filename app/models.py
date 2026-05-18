from typing import Any, Literal

from pydantic import BaseModel, Field


AgenticMode = Literal["auto", "agentic", "linear"]


class RecommendRequest(BaseModel):
    text: str = Field(min_length=3, max_length=500, description="Natural language user intent")
    target_count: int | None = Field(default=None, ge=1, le=50)
    agentic_mode: AgenticMode = "auto"


class IntentProfile(BaseModel):
    mood: str = "neutral"
    activity: str = "listening"
    genre: list[str] = Field(default_factory=list)
    energy: Literal["low", "medium", "high"] = "medium"
    language: Literal["id", "en"] = "id"
    locale: str = ""
    strict_locale: bool = False
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    target_audio: dict[str, float] = Field(default_factory=dict)
    seed_genres: list[str] = Field(default_factory=list)
    decade: str = ""


class TrackCandidate(BaseModel):
    title: str
    artist: str
    track_id: str = ""
    spotify_url: str = ""
    preview_url: str = ""
    popularity: int = 0
    score: float = 0.0
    why: str = ""
    audio_features: dict[str, float] | None = None
    lyric_signals: dict[str, Any] | None = None
    genres: list[str] = Field(default_factory=list)
    artist_ids: list[str] = Field(default_factory=list)


class RecommendationItem(BaseModel):
    rank: int
    title: str
    artist: str
    track_id: str = ""
    spotify_url: str
    preview_url: str
    why: str
    score: float
    audio_features: dict[str, float] | None = None
    lyric_signals: dict[str, Any] | None = None


class RecommendResponse(BaseModel):
    summary: dict
    intent_profile: IntentProfile
    query_strategy: dict
    recommendations: list[RecommendationItem]
    quality_notes: dict


class RefineRequest(BaseModel):
    previous_profile: IntentProfile
    previous_track_ids: list[str] = Field(default_factory=list, max_length=100)
    refinement_text: str = Field(min_length=3, max_length=200)
    target_count: int | None = Field(default=None, ge=1, le=50)
    agentic_mode: AgenticMode = "auto"
