"""
Configuration for News Llama web application.

Environment-based settings using Pydantic BaseSettings.
"""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "sqlite:///data/news_llama.db"

    # Security
    secret_key: str = "dev-secret-key-change-in-production"

    # Avatar Upload
    avatar_max_size_kb: int = 500
    avatar_max_width: int = 512
    avatar_max_height: int = 512
    avatar_directory: str = "src/web/static/avatars"

    # Newsletter
    newsletter_retention_days: int = 365
    output_directory: str = "output"

    # Scheduler
    scheduler_enabled: bool = True
    scheduler_hour: int = 6  # 6 AM daily generation
    scheduler_minute: int = 0

    # Application
    app_title: str = "News Llama"
    app_tagline: str = "No Drama, Just News Llama"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
