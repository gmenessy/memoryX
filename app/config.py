"""
Application Configuration using Pydantic Settings
"""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application Info
    app_name: str = Field(default="BrainDump NextGen", description="Application name")
    app_version: str = Field(default="0.0.1", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")

    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./braindump.db",
        description="Database connection URL"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="CORS allowed origins"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()