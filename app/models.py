from typing import Literal

from pydantic import BaseModel, Field


class RecommendRequest(BaseModel):
    text: str = Field(min_length=3, description="Natural language user intent")
    target_count: int | None = Field(default=None, ge=1, le=50)


class IntentProfile(BaseModel):
    mood: str = "neutral"
    activity: str = "listening"
    genre: list[str] = Field(default_factory=list)
    energy: Literal["low", "medium", "high"] = "medium"
    language: str = "id"
    locale: str = ""
    strict_locale: bool = False


class TrackCandidate(BaseModel):
    title: str
    artist: str
    spotify_url: str = ""
    preview_url: str = ""
    popularity: int = 0
    score: float = 0.0
    why: str = ""


class RecommendationItem(BaseModel):
    rank: int
    title: str
    artist: str
    spotify_url: str
    preview_url: str
    why: str
    score: float


class RecommendResponse(BaseModel):
    summary: dict
    intent_profile: IntentProfile
    query_strategy: dict
    recommendations: list[RecommendationItem]
    quality_notes: dict
