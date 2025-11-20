from __future__ import annotations

import re
from pathlib import Path
from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from ..core.models import PageText, Source
from ..core.ocr_runner import (
    OCRProcessError,
    extract_confidence_scores,
    queue_ocr_job,
    get_ocr_job_status,
    get_ocr_result,
    get_notifications,
    clear_notification,
    run_hybrid_ocr,
)
from ..core.parser import PERSON_PATTERN, PERSON_PATTERN_ALT, SPOUSE_PATTERN
from ..core.settings import get_settings
from ..db import get_session

router = APIRouter(prefix="/ocr", tags=["ocr"])


class PageTextResponse(BaseModel):
    id: int
    page_index: int
    text: str


class PageTextUpdateRequest(BaseModel):
    text: str


class LineValidation(BaseModel):
    line_number: int
    text: str
    is_valid: bool
    pattern_type: str | None  # "person", "spouse", or None


@router.post("/{source_id}")
def run_ocr_for_source(
    source_id: int,
    session: Session = Depends(get_session),
) -> JSONResponse:
    source = session.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    settings = get_settings()
    pdf_input = Path(source.path)
    if not pdf_input.exists():
        raise HTTPException(status_code=404, detail="Source file missing on disk")
    output_pdf = settings.ocr_dir / f"{pdf_input.stem}-ocr.pdf"

    try:
        job_id = queue_ocr_job(pdf_input, output_pdf)
    except OCRProcessError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return JSONResponse({"job_id": job_id})


@router.get("/notifications")
def get_all_notifications() -> JSONResponse:
    return JSONResponse(get_notifications())


@router.delete("/notifications/{notification_id}")
def delete_notification(notification_id: str) -> JSONResponse:
    clear_notification(notification_id)
    return JSONResponse({"status": "ok"})


@router.get("/{job_id}/progress")
def get_ocr_progress(job_id: str) -> JSONResponse:
    try:
        status = get_ocr_job_status(job_id)
        return JSONResponse(status)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{source_id}/status")
def ocr_status(
    source_id: int,
    job_id: str,
    include_confidence: bool = Body(False, embed=True),
    session: Session = Depends(get_session),
) -> JSONResponse:
    source = session.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    try:
        texts = get_ocr_result(job_id)
    except (ValueError, OCRProcessError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Optionally extract confidence scores
    confidences: List[tuple[float, str]] | None = None
    if include_confidence:
        try:
            confidences = extract_confidence_scores(Path(source.path))
        except OCRProcessError as exc:
            # Log error but don't fail the entire OCR if confidence extraction fails
            import logging
            logging.getLogger(__name__).error("Failed to extract confidence scores: %s", exc)

    existing = session.exec(select(PageText).where(PageText.source_id == source_id)).all()
    for record in existing:
        session.delete(record)

    for index, text in enumerate(texts):
        page = PageText(source_id=source_id, page_index=index, text=text)

        # Add confidence data if available
        if confidences and index < len(confidences):
            page.confidence = confidences[index][0]
            page.line_confidences = confidences[index][1]

        session.add(page)

    source.pages = len(texts)
    source.ocr_done = True
    source.stage = "ocr_done"
    session.add(source)
    session.commit()

    return JSONResponse({"pages": source.pages, "ocr_done": source.ocr_done})


@router.get("/{source_id}/text")
def get_ocr_text(source_id: int, session: Session = Depends(get_session)) -> List[PageTextResponse]:
    """Get all OCR text for a source for review/editing."""
    source = session.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    pages = session.exec(
        select(PageText)
        .where(PageText.source_id == source_id)
        .order_by(PageText.page_index)
    ).all()

    if not pages:
        raise HTTPException(status_code=404, detail="No OCR text found for this source")

    return [PageTextResponse(id=p.id, page_index=p.page_index, text=p.text) for p in pages]


@router.put("/{source_id}/text/{page_id}")
def update_ocr_text(
    source_id: int,
    page_id: int,
    payload: PageTextUpdateRequest,
    session: Session = Depends(get_session)
) -> JSONResponse:
    """Update OCR text for a specific page after user edits."""
    page_text = session.get(PageText, page_id)
    if not page_text or page_text.source_id != source_id:
        raise HTTPException(status_code=404, detail="Page not found")

    page_text.text = payload.text
    session.add(page_text)

    # Mark source as reviewed after any edits
    source = session.get(Source, source_id)
    if source and source.stage == "ocr_done":
        source.stage = "reviewed"
        session.add(source)

    session.commit()

    return JSONResponse({"status": "updated", "page_id": page_id})


@router.post("/{source_id}/validate")
def validate_ocr_text(
    source_id: int,
    text: str = Body(..., embed=True),
    session: Session = Depends(get_session)
) -> List[LineValidation]:
    """Validate OCR text lines against parser patterns."""
    source = session.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    lines = text.split('\n')
    validations = []

    for line_num, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue

        is_person = bool(PERSON_PATTERN.match(line)) or bool(PERSON_PATTERN_ALT.match(line))
        is_spouse = bool(SPOUSE_PATTERN.match(line))

        validations.append(LineValidation(
            line_number=line_num,
            text=line,
            is_valid=is_person or is_spouse,
            pattern_type="person" if is_person else ("spouse" if is_spouse else None)
        ))

    return validations


@router.get("/{source_id}/hybrid-comparison")
def get_hybrid_ocr_comparison(
    source_id: int,
    session: Session = Depends(get_session)
) -> JSONResponse:
    """
    Get hybrid OCR comparison between Tesseract and Ollama for debugging/review.

    Returns line-by-line comparison showing which source was selected for each line.
    """
    source = session.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    settings = get_settings()
    if not settings.ollama_enabled or not settings.ollama_use_hybrid_ocr:
        raise HTTPException(
            status_code=400,
            detail="Hybrid OCR is disabled. Enable with GENEALOGY_OLLAMA_ENABLED=true"
        )

    pdf_path = Path(source.path)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Source file missing on disk")

    # Check for OCR'd PDF
    ocr_pdf = settings.ocr_dir / f"{pdf_path.stem}-ocr.pdf"
    if not ocr_pdf.exists():
        raise HTTPException(
            status_code=400,
            detail="OCR must be completed first. Run OCR on this source before requesting hybrid comparison."
        )

    try:
        result = run_hybrid_ocr(ocr_pdf)
        return JSONResponse(result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Hybrid OCR failed: {str(exc)}")


@router.get("/{source_id}/confidence")
def get_confidence_breakdown(
    source_id: int,
    session: Session = Depends(get_session)
) -> JSONResponse:
    """Get detailed confidence score breakdown for all pages."""
    source = session.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    pages = session.exec(
        select(PageText)
        .where(PageText.source_id == source_id)
        .order_by(PageText.page_index)
    ).all()

    if not pages:
        raise HTTPException(status_code=404, detail="No OCR data found")

    result = {
        "source_id": source_id,
        "source_name": source.name,
        "pages": []
    }

    for page in pages:
        page_data = {
            "page_index": page.page_index,
            "confidence": page.confidence,
            "ocr_source": page.ocr_source,
            "tesseract_confidence": page.tesseract_confidence,
            "ollama_confidence": page.ollama_confidence,
            "selected_source": page.selected_source,
        }

        # Parse line confidences if available
        if page.line_confidences:
            import json
            try:
                page_data["line_confidences"] = json.loads(page.line_confidences)
            except json.JSONDecodeError:
                page_data["line_confidences"] = []

        result["pages"].append(page_data)

    return JSONResponse(result)
