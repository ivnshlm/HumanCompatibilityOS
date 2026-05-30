from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"

    # Default DSN points at the docker-compose `db` service. Override with DATABASE_URL.
    database_url: str = "postgresql+psycopg://hcos:hcos@db:5432/hcos"

    # JWT settings (used from Phase 1 onward).
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 30
    refresh_token_ttl_days: int = 14

    # Comma-separated list of extra allowed CORS origins (split-deploy / local dev).
    # Empty by default — the single-origin reverse-proxy deploy needs no CORS.
    cors_origins: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
