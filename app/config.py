from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    planner_mode: Literal["rule", "llm"] = "rule"
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.deepseek.com"
    openai_model: str = "deepseek-chat"

    def require_llm_credentials(self) -> None:
        if self.planner_mode == "llm" and not self.openai_api_key:
            raise ValueError("PLANNER_MODE=llm requires OPENAI_API_KEY")


@lru_cache
def get_settings() -> Settings:
    return Settings()
