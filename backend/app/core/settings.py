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

    # OCRmyPDF settings - automatically prefixed with GENEALOGY_ via env_prefix
    ocrmypdf_executable: str = Field(default="ocrmypdf")
    ocrmypdf_language: str = Field(default="eng")
    ocrmypdf_remove_background: bool = Field(default=False)
    ocrmypdf_fast_web_view_mb: int = Field(default=200)
    ocrmypdf_timeout_secs: int = Field(default=600)

    # LLM provider settings - choose between "ollama" or "openrouter"
    llm_provider: str = Field(default="ollama")  # Options: "ollama", "openrouter"

    # Ollama LLM settings for OCR correction and parsing
    ollama_enabled: bool = Field(default=False)
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_ocr_model: str = Field(default="llama3.2-vision:11b")  # Vision model for direct image OCR
    ollama_parse_model: str = Field(default="qwen3:8b")  # Text model for parsing
    ollama_timeout_secs: int = Field(default=30)
    ollama_use_hybrid_ocr: bool = Field(default=True)
    ollama_use_context_parse: bool = Field(default=True)
    ollama_confidence_threshold: float = Field(default=0.7)

    # OpenRouter LLM settings (cloud-based alternative to Ollama)
    openrouter_api_key: Optional[str] = Field(default=None)
    openrouter_ocr_model: str = Field(default="qwen/qwen2.5-vl-32b-instruct:free")  # Free vision model
    openrouter_parse_model: str = Field(default="meta-llama/llama-3.3-70b-instruct:free")  # Free text model
    openrouter_timeout_secs: int = Field(default=30)
    openrouter_use_hybrid_ocr: bool = Field(default=False)  # Disable hybrid OCR for cloud to save API calls
    openrouter_use_context_parse: bool = Field(default=True)

    model_config = SettingsConfigDict(
        env_prefix="GENEALOGY_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
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
