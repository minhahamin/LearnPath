from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str = ""
    tavily_api_key: str = ""

    database_url: str = "postgresql+asyncpg://curator:curator@localhost:5432/curator_db"

    max_react_iterations: int = 5
    max_retry_count: int = 2
    request_timeout_seconds: int = 30
    max_tokens_per_run: int = 50_000
    gemini_model: str = "gemini-2.5-flash"

    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
