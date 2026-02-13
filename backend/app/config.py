"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/bb_command"

    # Auth
    jwt_secret_key: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 1440  # 24 hours

    # Anthropic AI
    anthropic_api_key: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # App
    app_env: str = "development"
    app_debug: bool = True
    cors_origins: str = "http://localhost:5173"

    # AI Model Selection
    ai_model_heavy: str = "claude-opus-4-6"  # complex reasoning: triage, coaching, stats interpretation
    ai_model_light: str = "claude-sonnet-4-5-20250929"  # routine: data profiling, summarization, report drafts

    # Agent Settings
    agent_max_context_messages: int = 20  # messages before summarization kicks in
    agent_temperature: float = 0.3  # low temperature for consistent, methodical responses
    agent_max_tokens: int = 4096

    # File Storage
    storage_backend: str = "local"          # "local" or "s3"
    storage_local_path: str = "./uploads"
    s3_bucket: str = ""
    s3_region: str = "us-east-1"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_endpoint_url: str = ""               # For Supabase Storage / MinIO

    # Email / SMTP
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_address: str = "noreply@bbcommand.dev"
    smtp_from_name: str = "BB Enabled Command"
    email_enabled: bool = False             # Off by default, enable via env

    # App URLs
    app_base_url: str = "http://localhost:5173"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
