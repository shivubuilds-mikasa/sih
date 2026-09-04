"""Application configuration for SHARMI backend."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    APP_NAME: str = "sharmi-backend"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    model_config = {"env_prefix": "SHARMI_"}


settings = Settings()
