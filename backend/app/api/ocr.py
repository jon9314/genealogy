from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from ..core.models import PageText, Source
from ..core.ocr_runner import OCRProcessError, run_ocr
from ..core.settings import get_settings
from ..db import get_session

router = APIRouter(prefix="/ocr", tags=["ocr"])


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
