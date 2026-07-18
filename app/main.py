import logging
import secrets
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.models import RecommendRequest, RecommendResponse, RefineRequest
from app.services.pipeline import RecommendationPipeline
from app.services.prompt_store import PromptStore


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
)
logger = logging.getLogger(__name__)


# --- Cookie / session helpers ---------------------------------------------

SESSION_COOKIE = "sd_session"
OAUTH_STATE_COOKIE = "sd_oauth_state"
OAUTH_STATE_MAX_AGE = 600  # 10 minutes
SESSION_SALT = "sd-session"
OAUTH_STATE_SALT = "sd-oauth-state"

_session_serializer = URLSafeTimedSerializer(settings.session_secret, salt=SESSION_SALT)
_oauth_state_serializer = URLSafeTimedSerializer(settings.session_secret, salt=OAUTH_STATE_SALT)


def _set_cookie(
    response: Response,
    name: str,
    value: str,
    max_age: int,
    *,
    http_only: bool = True,
) -> None:
    response.set_cookie(
        key=name,
        value=value,
        max_age=max_age,
        httponly=http_only,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def _clear_cookie(response: Response, name: str) -> None:
    response.delete_cookie(key=name, path="/")


def _read_session(request: Request) -> dict | None:
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        return None
    try:
        # Built-in TTL: max age = expires_in baked into payload field.
        data = _session_serializer.loads(raw, max_age=60 * 60 * 24 * 30)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(data, dict):
        return None
    expires_at = float(data.get("expires_at", 0))
    if expires_at and expires_at < time.time():
        return None
    return data


# --- Rate limiter ---------------------------------------------------------

limiter = Limiter(key_func=get_remote_address)


# --- App lifespan ---------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pipeline.semantic.load()
    timeout = httpx.Timeout(connect=10.0, read=45.0, write=20.0, pool=10.0)
    limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
    async with httpx.AsyncClient(timeout=timeout, limits=limits, follow_redirects=False) as client:
        app.state.http_client = client
        app.state.pipeline.llm.attach_client(client)
        app.state.pipeline.spotify.attach_client(client)
        app.state.pipeline.genius.attach_client(client)
        app.state.prompt_store.attach_client(client)
        logger.info("SmartDiscover ready (model=%s)", app.state.pipeline.llm.model)
        yield


app = FastAPI(title="SmartDiscover API", version="0.2.0", lifespan=lifespan)
# Default (test/dev fallback) HTTP client; lifespan replaces it with a managed instance.
_default_http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(connect=10.0, read=45.0, write=20.0, pool=10.0),
    limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
    follow_redirects=False,
)
app.state.pipeline = RecommendationPipeline()
app.state.pipeline.llm.attach_client(_default_http_client)
app.state.pipeline.spotify.attach_client(_default_http_client)
app.state.pipeline.genius.attach_client(_default_http_client)
app.state.prompt_store = PromptStore()
app.state.prompt_store.attach_client(_default_http_client)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda req, exc: Response(
    content='{"detail":"rate limit exceeded"}',
    status_code=429,
    media_type="application/json",
))
app.mount("/static", StaticFiles(directory="web"), name="static")

# Backward-compatible module-level aliases (used by tests and external imports).
pipeline = app.state.pipeline
prompt_store = app.state.prompt_store


def get_pipeline(request: Request) -> RecommendationPipeline:
    return request.app.state.pipeline


def get_prompt_store(request: Request) -> PromptStore:
    return request.app.state.prompt_store


def get_spotify_token(request: Request) -> str:
    session = _read_session(request)
    if not session or not session.get("access_token"):
        raise HTTPException(
            status_code=401,
            detail="Spotify session expired or unauthorized. Please reconnect Spotify.",
        )
    return str(session["access_token"])


def _resolve_redirect_uri(request: Request) -> str:
    configured = settings.spotify_redirect_uri.strip()
    if configured:
        return configured
    return str(request.base_url) + "auth/callback"


# --- Schemas --------------------------------------------------------------


class CreatePlaylistRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=300)
    track_ids: list[str] = Field(default_factory=list, max_length=100)


# --- Routes ---------------------------------------------------------------


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse("web/index.html")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "smartdiscover-api"}


@app.get("/spotify/health")
async def spotify_health(pipeline: RecommendationPipeline = Depends(get_pipeline)) -> dict:
    status = await pipeline.spotify.health_check()
    return {"service": "spotify", **status}


@app.get("/llm/health")
async def llm_health(pipeline: RecommendationPipeline = Depends(get_pipeline)) -> dict:
    status = await pipeline.llm.health_check()
    return {"service": "openrouter", "model": pipeline.llm.model, **status}


@app.get("/api/prompt-suggestions")
@limiter.limit(settings.rate_limit_suggestions)
async def get_prompt_suggestions(
    request: Request,
    q: str = "",
    store: PromptStore = Depends(get_prompt_store),
) -> dict:
    if not store.enabled:
        return {"suggestions": []}
    safe_q = (q or "")[:100]
    suggestions = await store.search_suggestions(safe_q, limit=15)
    return {"suggestions": suggestions}


@app.post("/recommend", response_model=RecommendResponse)
@limiter.limit(settings.rate_limit_recommend)
async def recommend(
    request: Request,
    payload: RecommendRequest,
    pipeline: RecommendationPipeline = Depends(get_pipeline),
    store: PromptStore = Depends(get_prompt_store),
) -> RecommendResponse:
    response = await pipeline.run(payload)

    try:
        await store.save_prompt(
            prompt_text=payload.text,
            target_count=payload.target_count,
            source="web",
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except Exception as exc:  # save_prompt already swallows, but be defensive
        logger.warning("Failed to persist prompt to Supabase: %s", exc)

    return response


@app.post("/refine", response_model=RecommendResponse)
@limiter.limit(settings.rate_limit_recommend)
async def refine(
    request: Request,
    payload: RefineRequest,
    pipeline: RecommendationPipeline = Depends(get_pipeline),
) -> RecommendResponse:
    return await pipeline.run_refine(payload)


# --- OAuth flow -----------------------------------------------------------


@app.get("/auth/login")
def login(request: Request, pipeline: RecommendationPipeline = Depends(get_pipeline)):
    redirect_uri = _resolve_redirect_uri(request)
    state_nonce = secrets.token_urlsafe(24)
    state_signed = _oauth_state_serializer.dumps(state_nonce)
    url = pipeline.spotify.get_authorization_url(redirect_uri, state=state_nonce)
    response = RedirectResponse(url)
    _set_cookie(response, OAUTH_STATE_COOKIE, state_signed, max_age=OAUTH_STATE_MAX_AGE)
    return response


@app.get("/auth/callback")
@app.get("/callback")
async def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    pipeline: RecommendationPipeline = Depends(get_pipeline),
):
    if error:
        raise HTTPException(status_code=400, detail=f"Spotify OAuth error: {error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state in OAuth callback.")

    cookie_state_signed = request.cookies.get(OAUTH_STATE_COOKIE)
    if not cookie_state_signed:
        raise HTTPException(status_code=400, detail="OAuth state cookie missing or expired.")

    try:
        expected_state = _oauth_state_serializer.loads(cookie_state_signed, max_age=OAUTH_STATE_MAX_AGE)
    except (BadSignature, SignatureExpired):
        raise HTTPException(status_code=400, detail="OAuth state invalid or expired.")

    if not secrets.compare_digest(str(expected_state), str(state)):
        raise HTTPException(status_code=400, detail="OAuth state mismatch.")

    redirect_uri = _resolve_redirect_uri(request)
    try:
        token_info = await pipeline.spotify.get_user_token(code, redirect_uri)
    except Exception as exc:
        logger.warning("Spotify token exchange failed: %s", exc)
        raise HTTPException(status_code=502, detail="Spotify token exchange failed.")

    access_token = token_info.get("access_token")
    refresh_token = token_info.get("refresh_token", "")
    expires_in = int(token_info.get("expires_in", 3600))
    if not access_token:
        raise HTTPException(status_code=502, detail="Spotify did not return access_token.")

    session_payload = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": time.time() + max(60, expires_in - 60),
    }
    session_signed = _session_serializer.dumps(session_payload)

    response = RedirectResponse(url="/")
    _clear_cookie(response, OAUTH_STATE_COOKIE)
    _set_cookie(response, SESSION_COOKIE, session_signed, max_age=expires_in)
    return response


@app.post("/auth/logout")
def logout() -> Response:
    response = Response(status_code=204)
    _clear_cookie(response, SESSION_COOKIE)
    return response


@app.get("/auth/status")
def auth_status(request: Request) -> dict:
    session = _read_session(request)
    if not session:
        return {"connected": False}
    return {
        "connected": True,
        "expires_at": session.get("expires_at", 0),
    }


@app.post("/create-playlist")
async def create_playlist(
    payload: CreatePlaylistRequest,
    user_token: str = Depends(get_spotify_token),
    pipeline: RecommendationPipeline = Depends(get_pipeline),
) -> dict:
    try:
        return await pipeline.spotify.create_playlist(
            user_token=user_token,
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
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to create Spotify playlist due to an internal server error.",
        )
