from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    database_url: str
    llm_provider: str
    llm_temperature: float
    ollama_base_url: str
    ollama_model: str
    ollama_timeout_seconds: float
    openai_api_key: str | None
    openai_base_url: str
    openai_model: str
    openai_timeout_seconds: float
    gemini_api_key: str | None
    gemini_base_url: str
    gemini_model: str
    gemini_timeout_seconds: float
    app_timezone: str
    log_file_path: Path
    mock_data_dir: Path
    auto_seed: bool

    @property
    def database_path(self) -> Path:
        if self.database_url.startswith("sqlite:///"):
            raw_path = self.database_url.replace("sqlite:///", "", 1)
            path = Path(raw_path)
            if not path.is_absolute():
                path = PROJECT_ROOT / path
            return path
        raise ValueError("Only sqlite:/// database URLs are supported.")


def _bool_from_env(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache
def get_settings() -> Settings:
    log_path = Path(os.getenv("LOG_FILE_PATH", "logs/assistant.log"))
    if not log_path.is_absolute():
        log_path = PROJECT_ROOT / log_path

    mock_data_dir = Path(os.getenv("MOCK_DATA_DIR", "mock_data"))
    if not mock_data_dir.is_absolute():
        mock_data_dir = PROJECT_ROOT / mock_data_dir

    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///school_erp.db"),
        llm_provider=os.getenv("LLM_PROVIDER", "ollama"),
        llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0")),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1"),
        ollama_timeout_seconds=float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "2")),
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        openai_timeout_seconds=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "10")),
        gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
        gemini_base_url=os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        gemini_timeout_seconds=float(os.getenv("GEMINI_TIMEOUT_SECONDS", "10")),
        app_timezone=os.getenv("APP_TIMEZONE", "Asia/Calcutta"),
        log_file_path=log_path,
        mock_data_dir=mock_data_dir,
        auto_seed=_bool_from_env(os.getenv("AUTO_SEED"), True),
    )


def reset_settings_cache() -> None:
    get_settings.cache_clear()
