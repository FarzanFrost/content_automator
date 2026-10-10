"""Application configuration managed through pydantic-settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    GEMINI_API_KEY: str = Field(
        default="",
        description="Google Gemini API key",
    )
    DEFAULT_N_INFOGRAPHICS: int = Field(
        default=3,
        description="Default number of infographics to generate",
    )
    SHORTS_BGM_PATH: str = Field(
        default="",
        description="File path to default background music track",
    )
    BASE_OUTPUT_DIR: str = Field(
        default="",
        description="Root output directory path for project assets",
    )

    @classmethod
    def load(cls) -> "AppSettings":
        """Factory method to instantiate settings."""
        return cls()
