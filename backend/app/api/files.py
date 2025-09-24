from __future__ import annotations

import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import or_
from sqlmodel import Session, select

from ..core.models import Child, Family, PageText, Person, Source, SourceRead
from ..core.settings import get_settings
from ..db import get_session

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=List[SourceRead])
async def upload_files(
    files: List[UploadFile] = File(...),
    session: Session = Depends(get_session),
) -> List[SourceRead]:
    settings = get_settings()
    results: List[Source] = []
    for upload in files:
        if not upload.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"Unsupported file type for {upload.filename}")
        safe_name = f"{uuid.uuid4().hex}-{Path(upload.filename).name}"
        dest_path = settings.upload_dir / safe_name
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with dest_path.open("wb") as buffer:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                buffer.write(chunk)
        source = Source(name=upload.filename, path=str(dest_path))
        session.add(source)
        session.flush()
        results.append(source)
    session.commit()
    return results


@router.get("", response_model=List[SourceRead])
def list_files(session: Session = Depends(get_session)) -> List[SourceRead]:
    sources = session.exec(select(Source)).all()
    return list(sources)


@router.delete("/{source_id}")
def delete_file(source_id: int, session: Session = Depends(get_session)) -> JSONResponse:
    source = session.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    texts = session.exec(select(PageText).where(PageText.source_id == source_id)).all()
    for text in texts:
        session.delete(text)

    people = session.exec(select(Person).where(Person.source_id == source_id)).all()
    person_ids = {person.id for person in people if person.id is not None}

    if person_ids:
        children = session.exec(select(Child).where(Child.person_id.in_(person_ids))).all()
        for child in children:
            session.delete(child)

        families = session.exec(
            select(Family).where(
                or_(Family.husband_id.in_(person_ids), Family.wife_id.in_(person_ids))
            )
        ).all()
        for family in families:
            if family.husband_id in person_ids:
                family.husband_id = None
            if family.wife_id in person_ids:
                family.wife_id = None
            session.add(family)

    for person in people:
        session.delete(person)

    session.delete(source)
    session.commit()

    Path(source.path).unlink(missing_ok=True)
    return JSONResponse({"status": "deleted"})
