"""Application settings loaded from environment variables / .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Moomoo / OpenD ---
    # OpenD 本地网关。OpenD 内部自行完成登录，后端只需 host + port；
    # password 字段作为预留（未来如需配置 OpenD 登录用），不传给 SDK。
    moomoo_host: str = "127.0.0.1"
    moomoo_port: int = 11111
    moomoo_password: str = ""

    # --- AI（OpenAI 兼容端点）---
    ai_api_key: str = ""
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4o-mini"

    # --- Storage ---
    # SQLite by default so the app runs with zero infra; set DATABASE_URL to a
    # Postgres DSN (postgresql+psycopg2://...) in production / docker.
    database_url: str = "sqlite:///./market_intel.db"
    redis_url: str = "redis://localhost:6379/0"

    # --- News (Moomoo public endpoint) ---
    news_base_url: str = "https://ai-news-search.futunn.com"
    news_lang: str = "en"
    news_size: int = 20

    # --- Pipeline ---
    mover_top_n: int = 10
    cache_ttl_seconds: int = 60
    refresh_interval_minutes: int = 15

    # --- CORS (comma-separated origins) ---
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # --- App ---
    app_name: str = "Market Intel Engine"
    environment: str = "development"
    # Absolute path to the built frontend (dist). When set, FastAPI serves it.
    frontend_dist: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
