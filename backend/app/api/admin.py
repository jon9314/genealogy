"""Admin API endpoints for managing application data and settings."""

from __future__ import annotations

import logging
import os
from typing import Dict, Any, Optional, List
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, select, delete
import httpx

from ..core.models import Person, Family, Child, PageText, Source
from ..core.settings import get_settings
from ..db import get_session

router = APIRouter(prefix="/admin", tags=["admin"])
LOGGER = logging.getLogger(__name__)


class RateLimitSettings(BaseModel):
    """Rate limit configuration."""
    enabled: bool = Field(default=False, description="Enable rate limiting")
    max_requests_per_minute: int = Field(default=10, ge=1, le=1000, description="Maximum requests per minute")
    openrouter_only: bool = Field(default=True, description="Only apply to OpenRouter API calls")


class DeleteDataRequest(BaseModel):
    """Request to delete data."""
    confirm: bool = Field(description="Must be true to confirm deletion")
    delete_sources: bool = Field(default=False, description="Also delete uploaded PDF files")
    delete_ocr: bool = Field(default=False, description="Also delete OCR text")


class OpenRouterSettings(BaseModel):
    """OpenRouter configuration settings."""
    ocr_model: str = Field(description="Vision model for OCR")
    parse_model: str = Field(description="Text model for parsing")
    use_hybrid_ocr: bool = Field(description="Enable hybrid OCR (Tesseract + LLM)")
    use_context_parse: bool = Field(description="Enable LLM parsing fallback")
    confidence_threshold: float = Field(ge=0.0, le=1.0, description="Confidence threshold for LLM usage")


class ModelInfo(BaseModel):
    """Model information from OpenRouter."""
    id: str
    name: str
    is_vision: bool


# In-memory settings (could be moved to database or cache)
_rate_limit_settings: Optional[RateLimitSettings] = None
_openrouter_settings: Optional[OpenRouterSettings] = None


@router.delete("/data")
def delete_all_data(
    request: DeleteDataRequest,
    session: Session = Depends(get_session),
) -> JSONResponse:
    """
    Delete all parsed genealogy data.

    This removes:
    - All persons
    - All families
    - All child relationships
    - Optionally: OCR text
    - Optionally: Source files

    This is useful for starting over with a fresh parse.
    """
    if not request.confirm:
        raise HTTPException(status_code=400, detail="Must confirm deletion by setting confirm=true")

    stats = {
        "persons_deleted": 0,
        "families_deleted": 0,
        "children_deleted": 0,
        "ocr_deleted": 0,
        "sources_deleted": 0,
    }

    try:
        # Delete child relationships
        children = session.exec(select(Child)).all()
        for child in children:
            session.delete(child)
        stats["children_deleted"] = len(children)

        # Delete families
        families = session.exec(select(Family)).all()
        for family in families:
            session.delete(family)
        stats["families_deleted"] = len(families)

        # Delete persons
        persons = session.exec(select(Person)).all()
        for person in persons:
            session.delete(person)
        stats["persons_deleted"] = len(persons)

        # Optionally delete OCR text
        if request.delete_ocr:
            ocr_texts = session.exec(select(PageText)).all()
            for page_text in ocr_texts:
                session.delete(page_text)
            stats["ocr_deleted"] = len(ocr_texts)

        # Optionally delete sources
        if request.delete_sources:
            sources = session.exec(select(Source)).all()
            for source in sources:
                session.delete(source)
            stats["sources_deleted"] = len(sources)

        session.commit()

        LOGGER.info(f"Deleted all data: {stats}")

        return JSONResponse({
            "status": "success",
            "message": "All data deleted successfully",
            "stats": stats
        })

    except Exception as e:
        session.rollback()
        LOGGER.error(f"Failed to delete data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete data: {str(e)}")


@router.get("/rate-limit")
def get_rate_limit_settings() -> RateLimitSettings:
    """Get current rate limit settings."""
    global _rate_limit_settings

    if _rate_limit_settings is None:
        _rate_limit_settings = RateLimitSettings()

    return _rate_limit_settings


@router.post("/rate-limit")
def update_rate_limit_settings(settings: RateLimitSettings) -> JSONResponse:
    """Update rate limit settings."""
    global _rate_limit_settings

    _rate_limit_settings = settings

    LOGGER.info(f"Rate limit settings updated: enabled={settings.enabled}, max={settings.max_requests_per_minute}/min")

    return JSONResponse({
        "status": "success",
        "message": "Rate limit settings updated",
        "settings": settings.model_dump()
    })


@router.get("/stats")
def get_data_stats(session: Session = Depends(get_session)) -> JSONResponse:
    """Get statistics about current data."""
    persons_count = len(session.exec(select(Person)).all())
    families_count = len(session.exec(select(Family)).all())
    children_count = len(session.exec(select(Child)).all())
    sources_count = len(session.exec(select(Source)).all())
    ocr_pages_count = len(session.exec(select(PageText)).all())

    return JSONResponse({
        "persons": persons_count,
        "families": families_count,
        "children": children_count,
        "sources": sources_count,
        "ocr_pages": ocr_pages_count,
    })


@router.get("/openrouter/models")
async def get_openrouter_models() -> List[ModelInfo]:
    """
    Get available OpenRouter models.

    Filters to show only free models and categorizes them by vision capability.
    """
    settings = get_settings()

    if not settings.openrouter_api_key:
        raise HTTPException(status_code=400, detail="OpenRouter API key not configured")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}"
                }
            )
            response.raise_for_status()
            data = response.json()

        models = []
        for model in data.get("data", []):
            model_id = model.get("id", "")

            # Only include free models
            pricing = model.get("pricing", {})
            prompt_price = float(pricing.get("prompt", "999"))
            completion_price = float(pricing.get("completion", "999"))

            if prompt_price == 0 and completion_price == 0:
                # Check if it's a vision model
                architecture = model.get("architecture", {})
                modality = architecture.get("modality", "text")
                is_vision = modality == "multimodal" or "vision" in model_id.lower() or "vl" in model_id.lower()

                models.append(ModelInfo(
                    id=model_id,
                    name=model.get("name", model_id),
                    is_vision=is_vision
                ))

        LOGGER.info(f"Found {len(models)} free OpenRouter models")
        return models

    except httpx.HTTPError as e:
        LOGGER.error(f"Failed to fetch OpenRouter models: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch models: {str(e)}")


@router.get("/openrouter/settings")
def get_openrouter_settings() -> OpenRouterSettings:
    """Get current OpenRouter configuration."""
    global _openrouter_settings
    settings = get_settings()

    if _openrouter_settings is None:
        # Initialize from environment settings
        _openrouter_settings = OpenRouterSettings(
            ocr_model=settings.openrouter_ocr_model,
            parse_model=settings.openrouter_parse_model,
            use_hybrid_ocr=settings.openrouter_use_hybrid_ocr,
            use_context_parse=settings.openrouter_use_context_parse,
            confidence_threshold=settings.ollama_confidence_threshold,  # Shared threshold
        )

    return _openrouter_settings


@router.post("/openrouter/settings")
def update_openrouter_settings(new_settings: OpenRouterSettings) -> JSONResponse:
    """
    Update OpenRouter configuration settings.

    Note: These settings are stored in memory and will reset on server restart.
    To persist changes, update your .env file.
    """
    global _openrouter_settings

    _openrouter_settings = new_settings

    # Also update the .env file for persistence
    env_file = Path(".env")
    if env_file.exists():
        try:
            lines = env_file.read_text().splitlines()
            updated_lines = []

            settings_map = {
                "GENEALOGY_OPENROUTER_OCR_MODEL": new_settings.ocr_model,
                "GENEALOGY_OPENROUTER_PARSE_MODEL": new_settings.parse_model,
                "GENEALOGY_OPENROUTER_USE_HYBRID_OCR": str(new_settings.use_hybrid_ocr).lower(),
                "GENEALOGY_OPENROUTER_USE_CONTEXT_PARSE": str(new_settings.use_context_parse).lower(),
                "GENEALOGY_OLLAMA_CONFIDENCE_THRESHOLD": str(new_settings.confidence_threshold),
            }

            updated_keys = set()
            for line in lines:
                updated = False
                for key, value in settings_map.items():
                    if line.startswith(f"{key}="):
                        updated_lines.append(f"{key}={value}")
                        updated_keys.add(key)
                        updated = True
                        break
                if not updated:
                    updated_lines.append(line)

            # Add any missing settings
            for key, value in settings_map.items():
                if key not in updated_keys:
                    updated_lines.append(f"{key}={value}")

            env_file.write_text("\n".join(updated_lines) + "\n")
            LOGGER.info(f"Updated .env file with new OpenRouter settings")

        except Exception as e:
            LOGGER.warning(f"Failed to update .env file: {e}")

    LOGGER.info(f"OpenRouter settings updated: {new_settings}")

    return JSONResponse({
        "status": "success",
        "message": "OpenRouter settings updated (restart server to fully apply changes)",
        "settings": new_settings.model_dump()
    })
