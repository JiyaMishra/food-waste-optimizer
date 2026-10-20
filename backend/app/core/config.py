"""Environment-based configuration for the Person B backend.

The repository root is added to ``sys.path`` so the backend can use Person A's
documented modules (``src.data``, ``src.availability``, ``src.features`` and
``src.ml``) without copying their logic.
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Autonomous Food Waste Optimization API"
    app_version: str = "1.0.0"
    environment: str = "local"
    api_v1_prefix: str = "/api/v1"

    # Local development defaults to SQLite. Set DATABASE_URL to a PostgreSQL
    # DSN (postgresql+psycopg://user:password@host:5432/db) in .env for the real
    # deployment. Tests override the FastAPI dependency with a temporary DB.
    database_url: str = f"sqlite:///{(PROJECT_ROOT / 'backend' / 'data' / 'food_optimizer.db').as_posix()}"
    sql_echo: bool = False

    data_dir: str = str(PROJECT_ROOT / "data" / "generated")
    menu_seed_path: str = str(PROJECT_ROOT / "data" / "menu_seed" / "vegetarian_menu.csv")
    model_artifact_path: str = str(PROJECT_ROOT / "ml" / "artifacts" / "context_model.joblib")

    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    log_level: str = "INFO"
    max_page_size: int = 200
    attendance_probability: float = 0.65
    default_consumption_rate: float = 0.85

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def data_path(self) -> Path:
        return Path(self.data_dir)

    @property
    def menu_seed_file(self) -> Path:
        return Path(self.menu_seed_path)

    @property
    def artifact_file(self) -> Path:
        return Path(self.model_artifact_path)

    def ensure_directories(self) -> None:
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.artifact_file.parent.mkdir(parents=True, exist_ok=True)
        (PROJECT_ROOT / "backend" / "data").mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
