from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    project_name: str = "GenealogyApp"
    api_prefix: str = "/api"
    data_dir: Path = Field(default=Path("./data"))
    upload_dir: Path = Field(default=Path("./data/uploads"))
    ocr_dir: Path = Field(default=Path("./data/ocr"))
    project_dir: Path = Field(default=Path("./data/projects"))
    database_path: Path = Field(default=Path("./data/app.db"))
    database_echo: bool = False

    ocrmypdf_executable: str = "ocrmypdf"
    ocrmypdf_language: str = "eng"
    ocrmypdf_remove_background: bool = False
    ocrmypdf_timeout_secs: int = 600

    model_config = SettingsConfigDict(
        env_prefix="GENEALOGY_",
        case_sensitive=False,
    )

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path.as_posix()}"

    def ensure_directories(self) -> None:
        for path in (self.data_dir, self.upload_dir, self.ocr_dir, self.project_dir, self.database_path.parent):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
