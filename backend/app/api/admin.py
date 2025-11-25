"""Admin API endpoints for managing application data and settings."""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, select, delete

from ..core.models import Person, Family, Child, PageText, Source
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


# In-memory rate limit settings (could be moved to database or cache)
_rate_limit_settings: Optional[RateLimitSettings] = None


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
