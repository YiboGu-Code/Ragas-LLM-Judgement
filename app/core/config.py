from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    sqlite_path: str = "data/app.db"
    dataset_dir: str = "data/datasets"
    artifact_dir: str = "artifacts"
    save_raw_datasets: bool = True
    save_artifacts: bool = True
    default_max_concurrency: int = 4
    default_timeout_seconds: int = 120

    model_config = SettingsConfigDict(env_prefix="APP_")
