from __future__ import annotations

import re
from pathlib import Path
from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from ..core.models import PageText, Source
from ..core.ocr_runner import OCRProcessError, run_ocr
from ..core.parser import PERSON_PATTERN, SPOUSE_PATTERN
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
def run_ocr_for_source(source_id: int, session: Session = Depends(get_session)) -> JSONResponse:
    source = session.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    settings = get_settings()
    pdf_input = Path(source.path)
    if not pdf_input.exists():
        raise HTTPException(status_code=404, detail="Source file missing on disk")
    output_pdf = settings.ocr_dir / f"{pdf_input.stem}-ocr.pdf"

    try:
        texts = run_ocr(pdf_input, output_pdf)
    except OCRProcessError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    existing = session.exec(select(PageText).where(PageText.source_id == source_id)).all()
    for record in existing:
        session.delete(record)

    for index, text in enumerate(texts):
        page = PageText(source_id=source_id, page_index=index, text=text)
        session.add(page)

    source.pages = len(texts)
    source.ocr_done = True
    session.add(source)
    session.commit()

    return JSONResponse({"pages": source.pages, "ocr_done": source.ocr_done})


@router.get("/{source_id}")
def ocr_status(source_id: int, session: Session = Depends(get_session)) -> JSONResponse:
    source = session.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    page_count = len(session.exec(select(PageText).where(PageText.source_id == source_id)).all())
    return JSONResponse({"pages": page_count, "ocr_done": source.ocr_done})


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

        is_person = bool(PERSON_PATTERN.match(line))
        is_spouse = bool(SPOUSE_PATTERN.match(line))

        validations.append(LineValidation(
            line_number=line_num,
            text=line,
            is_valid=is_person or is_spouse,
            pattern_type="person" if is_person else ("spouse" if is_spouse else None)
        ))

    return validations
