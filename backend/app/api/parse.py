from __future__ import annotations

import threading
import uuid
from typing import Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import Session, delete, select

from ..core.models import Child, Family, PageText, Person, Source
from ..core.parser import parse_ocr_text
from ..db import get_session

router = APIRouter(prefix="/parse", tags=["parse"])

# In-memory job store. In a production environment, you would use a more robust
# solution like Redis or a database.
PARSE_JOBS: Dict[str, Dict] = {}


def run_parse_in_background(
    job_id: str, source_id: int, db_url: str, page_indexes: Optional[List[int]] = None
):
    from sqlalchemy import create_engine
    from sqlmodel import Session

    engine = create_engine(db_url)
    with Session(engine) as session:
        source = session.get(Source, source_id)
        if not source:
            PARSE_JOBS[job_id] = {"status": "failed", "error": "Source not found"}
            return

        page_texts: List[PageText] = session.exec(
            select(PageText)
            .where(PageText.source_id == source_id)
            .order_by(PageText.page_index)
        ).all()
        if not page_texts:
            PARSE_JOBS[job_id] = {
                "status": "failed",
                "error": "OCR has not been run for this source",
            }
            return

        if page_indexes:
            # Incremental parse: only delete data from the specified pages
            session.exec(delete(Child).where(Child.family_id.in_(select(Family.id).where(Family.source_id == source_id, Family.page_index.in_(page_indexes)))))
            session.exec(delete(Family).where(Family.source_id == source_id, Family.page_index.in_(page_indexes)))
            session.exec(delete(Person).where(Person.source_id == source_id, Person.page_index.in_(page_indexes)))
        else:
            # Full parse: delete all data for the source
            session.exec(delete(Child).where(Child.family_id.in_(select(Family.id).where(Family.source_id == source_id))))
            session.exec(delete(Family).where(Family.source_id == source_id))
            session.exec(delete(Person).where(Person.source_id == source_id))
        session.commit()

        def progress_callback(current: int, total: int):
            PARSE_JOBS[job_id]["progress"] = {"current": current, "total": total}

        stats = parse_ocr_text(
            session,
            source_id=source_id,
            pages=[page.text for page in page_texts],
            page_indexes=page_indexes,
            progress_callback=progress_callback,
        )

        source.stage = "parsed"
        session.add(source)
        session.commit()
        PARSE_JOBS[job_id]["status"] = "completed"
        PARSE_JOBS[job_id]["stats"] = stats


@router.post("/{source_id}")
def parse_source(
    source_id: int,
    page_indexes: Optional[List[int]] = Body(None, embed=True),
    session: Session = Depends(get_session),
) -> JSONResponse:
    source = session.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    job_id = str(uuid.uuid4())
    PARSE_JOBS[job_id] = {"status": "running", "progress": {"current": 0, "total": 1}}

    from ..core.settings import get_settings

    db_url = get_settings().database_url
    thread = threading.Thread(
        target=run_parse_in_background, args=(job_id, source_id, db_url, page_indexes)
    )
    thread.start()

    return JSONResponse({"job_id": job_id})


@router.get("/{job_id}/progress")
def get_parse_progress(job_id: str) -> JSONResponse:
    job = PARSE_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JSONResponse(job)


@router.post("/{source_id}/preview")
def preview_parse(source_id: int, session: Session = Depends(get_session)) -> JSONResponse:
    """
    Preview what would be parsed without committing to database.
    Returns statistics and sample data for user confirmation.
    """
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

    # Parse in a transaction but don't commit
    stats = parse_ocr_text(
        session,
        source_id=source_id,
        pages=[page.text for page in page_texts],
    )

    # Get sample data before rollback
    people = session.exec(select(Person).where(Person.source_id == source_id).limit(10)).all()
    families = session.exec(select(Family).where(Family.source_id == source_id).limit(5)).all()

    sample_people = [
        {
            "id": p.id,
            "name": p.name,
            "gen": p.gen,
            "birth": p.birth,
            "death": p.death,
            "surname": p.surname,
        }
        for p in people
    ]

    sample_families = [
        {
            "id": f.id,
            "husband_id": f.husband_id,
            "wife_id": f.wife_id,
        }
        for f in families
    ]

    # Rollback to avoid committing the preview data
    session.rollback()

    return JSONResponse(
        {
            "people": stats.get("people", 0),
            "families": stats.get("families", 0),
            "children": stats.get("children", 0),
            "flagged_lines": stats.get("flagged_lines", []),
            "sample_people": sample_people,
            "sample_families": sample_families,
        }
    )


@router.get("/{source_id}/status")
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


@router.get("/version-check")
def check_parser_versions(session: Session = Depends(get_session)) -> JSONResponse:
    """
    Check which sources need re-parsing due to outdated parser version.
    Returns list of sources with their current parser version vs latest version.
    """
    from ..core.parser import PARSER_VERSION

    sources = session.exec(select(Source).where(Source.stage == "parsed")).all()

    outdated_sources = []
    current_sources = []

    for source in sources:
        source_info = {
            "id": source.id,
            "name": source.name,
            "current_version": source.parser_version,
            "latest_version": PARSER_VERSION,
            "needs_reparse": source.parser_version != PARSER_VERSION
        }

        if source.parser_version != PARSER_VERSION:
            outdated_sources.append(source_info)
        else:
            current_sources.append(source_info)

    return JSONResponse({
        "latest_version": PARSER_VERSION,
        "outdated_count": len(outdated_sources),
        "current_count": len(current_sources),
        "outdated_sources": outdated_sources,
        "current_sources": current_sources
    })
