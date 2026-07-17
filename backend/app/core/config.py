"""Application configuration using pydantic-settings."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "Mia's Reminder"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-this-in-production"
    api_version: str = "v1"

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/ai_assistant"
    database_sync_url: str = "postgresql://user:password@localhost:5432/ai_assistant"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Firebase
    firebase_credentials_path: str = "./firebase-credentials.json"
    firebase_project_id: str = ""

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_max_tokens: int = 4096

    # Telegram
    telegram_bot_token: str = ""
    telegram_webhook_url: str = ""

    # FCM
    fcm_server_key: str = ""

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:8080"

    # Allowed hosts for production (comma-separated)
    allowed_hosts: str = "*"

    # Rate Limiting
    rate_limit_per_minute: int = 60

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
