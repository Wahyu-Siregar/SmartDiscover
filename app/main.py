from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.models import RecommendRequest, RecommendResponse
from app.services.pipeline import RecommendationPipeline


class CreatePlaylistRequest(BaseModel):
    user_token: str
    title: str
    description: str
    track_ids: list[str]

app = FastAPI(title="SmartDiscover API", version="0.1.0")
pipeline = RecommendationPipeline()
app.mount("/static", StaticFiles(directory="web"), name="static")


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


@app.post("/recommend", response_model=RecommendResponse)
async def recommend(payload: RecommendRequest) -> RecommendResponse:
    return await pipeline.run(payload)


@app.get("/auth/login")
def login(request: Request):
    # Construct redirect URI based on the incoming request to be dynamic
    redirect_uri = str(request.base_url) + "auth/callback"
    url = pipeline.spotify.get_authorization_url(redirect_uri)
    return RedirectResponse(url)


@app.get("/auth/callback")
async def callback(request: Request, code: str):
    redirect_uri = str(request.base_url) + "auth/callback"
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
    return await pipeline.spotify.create_playlist(
        user_token=payload.user_token,
        title=payload.title,
        description=payload.description,
        track_ids=payload.track_ids
    )
