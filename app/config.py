from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = Field(
        default="",
        validation_alias="OPENAI_API_KEY",
        description="Ключ API; можно задать только в .env",
    )
    openai_model: str = Field(
        default="gpt-4.1-mini",
        validation_alias="OPENAI_MODEL",
        description="Модель с vision: gpt-4.1 или gpt-4.1-mini",
    )


settings = Settings()
