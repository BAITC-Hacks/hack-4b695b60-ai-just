from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent

_SQLITE_PREFIX = "sqlite:///"


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "dev"
    database_url: str = "sqlite:///./app.db"
    seed_dir: Path = Path("../data/seed")
    seed_on_startup: bool = True
    cors_origins: str = "http://localhost:5173"

    ai_provider: str = "auto"
    ai_provider_chain: str = "openai,nvidia,brev,stub"
    ai_timeout_seconds: float = 25.0
    ai_max_repair_attempts: int = 1
    ai_redact_pii: bool = True

    openai_api_key: str = ""
    openai_model: str = "gpt-6-luna"
    openai_reasoning_effort: str = "low"
    openai_embed_model: str = "text-embedding-3-small"

    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "nvidia/nemotron-3-nano-30b-a3b"
    nvidia_embed_model: str = "nvidia/nemotron-3-embed-1b"

    brev_llm_base_url: str = ""
    brev_llm_model: str = "nemotron-3-nano"
    brev_llm_api_key: str = ""

    embed_provider_chain: str = "nvidia,openai,tfidf"

    @field_validator("database_url")
    @classmethod
    def _anchor_sqlite_path(cls, value: str) -> str:
        """Относительный путь SQLite считаем от папки backend/, а не от текущей директории."""
        if not value.startswith(_SQLITE_PREFIX):
            return value
        raw = value[len(_SQLITE_PREFIX) :]
        if raw in ("", ":memory:") or raw.startswith("/") or Path(raw).is_absolute():
            return value
        return _SQLITE_PREFIX + (BACKEND_DIR / raw).resolve().as_posix()

    @field_validator("seed_dir")
    @classmethod
    def _anchor_seed_dir(cls, value: Path) -> Path:
        return value if value.is_absolute() else (BACKEND_DIR / value).resolve()

    @property
    def cors_origin_list(self) -> list[str]:
        return _split_csv(self.cors_origins)

    @property
    def ai_chain(self) -> list[str]:
        return _split_csv(self.ai_provider_chain)

    @property
    def embed_chain(self) -> list[str]:
        return _split_csv(self.embed_provider_chain)


@lru_cache
def get_settings() -> Settings:
    return Settings()
