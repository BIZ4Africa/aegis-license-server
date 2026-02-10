"""
AEGIS License Server - Configuration
Uses Pydantic Settings for type-safe config from environment variables.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, PostgresDsn, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings can be overridden via .env file or environment variables.
    Example: DATABASE_URL=postgresql://user:pass@localhost/aegis
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # ===== Application =====
    app_name: str = Field(default="AEGIS License Server", description="Application name")
    app_version: str = Field(default="0.8.0", description="API version")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="production", description="Environment: development, staging, production")
    
    # ===== Server =====
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    reload: bool = Field(default=False, description="Auto-reload on code changes")
    
    # ===== Database =====
    database_url: PostgresDsn = Field(
        default="postgresql://aegis:aegis@localhost:5432/aegis",
        description="PostgreSQL connection URL"
    )
    db_echo: bool = Field(default=False, description="Echo SQL queries")
    db_pool_size: int = Field(default=5, description="Database connection pool size")
    db_max_overflow: int = Field(default=10, description="Max overflow connections")
    
    # ===== Security - Signing Keys =====
    private_key_path: Path = Field(
        default=Path("keys/aegis-2026-01.private.pem"),
        description="Path to Ed25519 private key for signing licenses"
    )
    public_key_path: Path = Field(
        default=Path("keys/aegis-2026-01.public.pem"),
        description="Path to Ed25519 public key (for verification)"
    )
    key_id: str = Field(
        default="aegis-2026-01",
        description="Key ID for JWT 'kid' header"
    )
    
    # ===== Security - API Authentication =====
    api_secret_key: str = Field(
        default="CHANGE_ME_IN_PRODUCTION_USE_LONG_RANDOM_STRING",
        description="Secret key for API authentication (JWT for admin access)"
    )
    api_access_token_expire_minutes: int = Field(
        default=60,
        description="API access token expiration (minutes)"
    )
    
    # ===== License Settings =====
    license_issuer: str = Field(
        default="https://license.biz4a.com",
        description="License issuer URL (JWT 'iss' claim)"
    )
    default_demo_duration_days: int = Field(
        default=30,
        description="Default demo license duration"
    )
    
    # ===== Rate Limiting =====
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, description="Max requests per minute")
    
    # ===== CORS =====
    cors_enabled: bool = Field(default=True, description="Enable CORS")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "https://portal.biz4a.com"],
        description="Allowed CORS origins"
    )
    
    # ===== Logging =====
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format: json or text")
    
    @validator("private_key_path", "public_key_path")
    def validate_key_paths(cls, v: Path) -> Path:
        """Ensure key paths are absolute."""
        if not v.is_absolute():
            # Make relative to project root
            return Path(__file__).parent.parent / v
        return v
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() == "production"
    
    def get_database_url_sync(self) -> str:
        """Get synchronous database URL (for Alembic)."""
        return str(self.database_url).replace("+asyncpg", "")
    
    def get_database_url_async(self) -> str:
        """Get async database URL (for SQLAlchemy async)."""
        url = str(self.database_url)
        if "asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://")
        return url


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    This function is cached to avoid re-reading environment variables
    on every call. Invalidate cache if settings need to be reloaded.
    """
    return Settings()


# Convenience exports
settings = get_settings()
