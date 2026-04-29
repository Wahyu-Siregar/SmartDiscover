from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    spotify_client_id: str = Field(default="", validation_alias="SPOTIFY_CLIENT_ID")
    spotify_client_secret: str = Field(default="", validation_alias="SPOTIFY_CLIENT_SECRET")
    spotify_redirect_uri: str = Field(default="", validation_alias="SPOTIFY_REDIRECT_URI")

    openrouter_api_key: str = Field(default="", validation_alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field(
        default="google/gemini-2.5-flash-lite",
        validation_alias="OPENROUTER_MODEL",
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        validation_alias="OPENROUTER_BASE_URL",
    )

    top_k_default: int = Field(default=15, validation_alias="TOP_K_DEFAULT")

    supabase_url: str = Field(default="", validation_alias="SUPABASE_URL")
    supabase_api_key: str = Field(default="", validation_alias="SUPABASE_API_KEY")
    supabase_prompt_table: str = Field(default="prompt_logs", validation_alias="SUPABASE_PROMPT_TABLE")

    session_secret: str = Field(default="dev-only-insecure-secret-change-me", validation_alias="SESSION_SECRET")
    ip_hash_salt: str = Field(default="dev-only-salt", validation_alias="IP_HASH_SALT")
    rate_limit_recommend: str = Field(default="10/minute", validation_alias="RATE_LIMIT_RECOMMEND")
    rate_limit_suggestions: str = Field(default="30/minute", validation_alias="RATE_LIMIT_SUGGESTIONS")
    app_public_url: str = Field(default="http://localhost:8000", validation_alias="APP_PUBLIC_URL")
    spotify_default_market: str = Field(default="ID", validation_alias="SPOTIFY_DEFAULT_MARKET")
    cookie_secure: bool = Field(default=False, validation_alias="COOKIE_SECURE")

    agent_loop_enabled: bool = Field(default=False, validation_alias="AGENT_LOOP_ENABLED")
    agent_loop_max_iterations: int = Field(default=3, validation_alias="AGENT_LOOP_MAX_ITERATIONS")
    agent_loop_timeout_s: float = Field(default=30.0, validation_alias="AGENT_LOOP_TIMEOUT_S")
    audio_feature_cache_ttl_s: int = Field(default=86400, validation_alias="AUDIO_FEATURE_CACHE_TTL_S")
    eval_pass_threshold: float = Field(default=0.7, validation_alias="EVAL_PASS_THRESHOLD")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
