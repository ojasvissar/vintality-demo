"""Application configuration from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    database_url: str = "postgresql://vintality:vintality_dev@localhost:5432/vintality"
    claude_model: str = "claude-sonnet-4-20250514"
    visual_crossing_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
