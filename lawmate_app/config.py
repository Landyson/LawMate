from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

def _resolve_project_root() -> Path:
    """Resolve the directory where we should look for `.env`.

    In development, this is the repository root (folder that contains
    `lawmate_app/`).

    When bundled with PyInstaller, `__file__` lives inside the internal
    bundle folder (e.g. `dist/Lawmate/_internal/...`). In that case we
    want to load `.env` from the directory where the executable lives.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


PROJECT_ROOT = _resolve_project_root()
load_dotenv(PROJECT_ROOT / ".env", override=False)

@dataclass(frozen=True)
class AppConfig:
    llm_provider: str
    openai_api_key: str
    openai_model: str
    ollama_api_key: str
    ollama_base_url: str
    ollama_model: str
    justice_lookback_days: int
    justice_max_items_per_day: int

    @staticmethod
    def load() -> "AppConfig":
        return AppConfig(
            llm_provider=os.getenv("LLM_PROVIDER", "mock").strip().lower(),
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip(),
            ollama_api_key=os.getenv("OLLAMA_API_KEY", "").strip(),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip(),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1:8b").strip(),
            justice_lookback_days=int(os.getenv("JUSTICE_LOOKBACK_DAYS", "14")),
            justice_max_items_per_day=int(os.getenv("JUSTICE_MAX_ITEMS_PER_DAY", "200")),
        )
