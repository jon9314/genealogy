from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import Session, delete, select

from ..core.models import Child, Family, PageText, Person, Source
from ..core.parser import parse_ocr_text
from ..db import get_session

router = APIRouter(prefix="/parse", tags=["parse"])


@router.post("/{source_id}")
def parse_source(source_id: int, session: Session = Depends(get_session)) -> JSONResponse:
    source = session.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    page_texts: List[PageText] = session.exec(
        select(PageText)
        .where(PageText.source_id == source_id)
        .order_by(PageText.page_index)
    ).all()
    if not page_texts:
        raise HTTPException(status_code=400, detail="OCR has not been run for this source")

    session.exec(delete(Child).where(Child.family_id.in_(select(Family.id).where(Family.source_id == source_id))))
    session.exec(delete(Family).where(Family.source_id == source_id))
    session.exec(delete(Person).where(Person.source_id == source_id))
    session.commit()

    stats = parse_ocr_text(
        session,
        source_id=source_id,
        pages=[page.text for page in page_texts],
    )

    # Update source stage to parsed
    source.stage = "parsed"
    session.add(source)
    session.commit()

    return JSONResponse(
        {
            "people": stats.get("people", 0),
            "families": stats.get("families", 0),
            "children": stats.get("children", 0),
            "flagged_lines": stats.get("flagged_lines", []),
        }
    )


@router.get("/{source_id}")
def parse_status(source_id: int, session: Session = Depends(get_session)) -> JSONResponse:
    people = session.exec(select(Person).where(Person.source_id == source_id)).all()
    families = session.exec(select(Family).where(Family.source_id == source_id)).all()
    children = session.exec(
        select(Child)
        .join(Family, Child.family_id == Family.id)
        .where(Family.source_id == source_id)
    ).all()
    return JSONResponse(
        {
            "people": len(people),
            "families": len(families),
            "children": len(children),
        }
    )
