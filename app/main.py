import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import logging

from app.config import settings
from app.models import RecommendRequest, RecommendResponse
from app.services.pipeline import RecommendationPipeline
from app.services.prompt_store import PromptStore


class CreatePlaylistRequest(BaseModel):
    user_token: str
    title: str
    description: str
    track_ids: list[str]

app = FastAPI(title="SmartDiscover API", version="0.1.0")
pipeline = RecommendationPipeline()
prompt_store = PromptStore()
logger = logging.getLogger(__name__)
app.mount("/static", StaticFiles(directory="web"), name="static")


def _resolve_redirect_uri(request: Request) -> str:
    # If explicitly configured (recommended for production), use it as-is.
    configured = settings.spotify_redirect_uri.strip()
    if configured:
        return configured

    # Fallback for local/dev environments.
    return str(request.base_url) + "auth/callback"


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse("web/index.html")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "smartdiscover-api"}


@app.get("/spotify/health")
async def spotify_health() -> dict:
    status = await pipeline.spotify.health_check()
    return {"service": "spotify", **status}


@app.get("/llm/health")
async def llm_health() -> dict:
    status = await pipeline.llm.health_check()
    return {"service": "openrouter", "model": pipeline.llm.model, **status}


@app.get("/api/prompt-suggestions")
async def get_prompt_suggestions(q: str = "") -> dict:
    """Fetch distinct prompts from database matching query text for autocomplete."""
    if not prompt_store.enabled:
        return {"suggestions": []}

    try:
        from urllib.parse import quote
        endpoint = f"{prompt_store._url}/rest/v1/{prompt_store._table}?select=prompt_text&order=created_at.desc&limit=15"
        
        # Add filter if query provided
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            endpoint += f"&prompt_text=ilike.{quote(pattern)}"
        
        headers = {
            "apikey": prompt_store._api_key,
            "Authorization": f"Bearer {prompt_store._api_key}",
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(endpoint, headers=headers)
            if response.status_code == 200:
                data = response.json()
                # Remove duplicates while preserving order
                seen = set()
                suggestions = []
                for row in data:
                    prompt = row.get("prompt_text", "").strip()
                    if prompt and prompt not in seen:
                        suggestions.append(prompt)
                        seen.add(prompt)
                return {"suggestions": suggestions[:15]}
        return {"suggestions": []}
    except Exception as exc:
        logger.warning("Failed to fetch prompt suggestions: %s", exc)
        return {"suggestions": []}


@app.post("/recommend", response_model=RecommendResponse)
async def recommend(payload: RecommendRequest, request: Request) -> RecommendResponse:
    response = await pipeline.run(payload)

    try:
        await prompt_store.save_prompt(
            prompt_text=payload.text,
            target_count=payload.target_count,
            source="web",
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except Exception as exc:
        logger.warning("Failed to persist prompt to Supabase: %s", exc)

    return response


@app.get("/auth/login")
def login(request: Request):
    redirect_uri = _resolve_redirect_uri(request)
    url = pipeline.spotify.get_authorization_url(redirect_uri)
    return RedirectResponse(url)


@app.get("/auth/callback")
@app.get("/callback")
async def callback(request: Request, code: str):
    redirect_uri = _resolve_redirect_uri(request)
    try:
        token_info = await pipeline.spotify.get_user_token(code, redirect_uri)
        # We redirect back to UI with token as hash/query param for the frontend to pick up
        # Real apps might use secure cookies/session instead
        access_token = token_info.get("access_token")
        return RedirectResponse(url=f"/?token={access_token}")
    except Exception as exc:
        return {"error": str(exc)}


@app.post("/create-playlist")
async def create_playlist(payload: CreatePlaylistRequest) -> dict:
    try:
        return await pipeline.spotify.create_playlist(
            user_token=payload.user_token,
            title=payload.title,
            description=payload.description,
            track_ids=payload.track_ids,
        )
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code if exc.response is not None else 500
        if status == 401:
            raise HTTPException(
                status_code=401,
                detail="Spotify session expired or unauthorized. Please reconnect Spotify.",
            )
        raise HTTPException(
            status_code=status,
            detail=f"Spotify API error ({status}).",
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to create Spotify playlist due to an internal server error.",
        )
