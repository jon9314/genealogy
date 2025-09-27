from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import SQLModel, Session, delete, select

from ..core.models import (
    Child,
    Family,
    PageText,
    Person,
    ProjectPayload,
    Source,
)
from ..core.settings import get_settings
from ..db import get_session

router = APIRouter(prefix="/project", tags=["project"])


class ProjectSaveRequest(SQLModel):
    filename: Optional[str] = None


class ProjectOpenRequest(SQLModel):
    filename: str


@router.post("/save")
def save_project(
    payload: ProjectSaveRequest | None = None,
    session: Session = Depends(get_session),
) -> JSONResponse:
    settings = get_settings()
    data = ProjectPayload(
        exported_at=datetime.utcnow(),
        sources=list(session.exec(select(Source)).all()),
        pages=list(session.exec(select(PageText)).all()),
        persons=list(session.exec(select(Person)).all()),
        families=list(session.exec(select(Family)).all()),
        children=list(session.exec(select(Child)).all()),
    )
    filename = payload.filename if payload and payload.filename else _timestamped_filename("project", "json")
    target = settings.project_dir / filename
    with target.open("w", encoding="utf-8") as fp:
        json.dump(data.model_dump(), fp, default=str, indent=2)

    last_pointer = settings.data_dir / "lastProject.json"
    with last_pointer.open("w", encoding="utf-8") as fp:
        json.dump({"path": str(target)}, fp)

    return JSONResponse({"status": "saved", "filename": filename})


@router.post("/open")
def open_project(payload: ProjectOpenRequest, session: Session = Depends(get_session)) -> JSONResponse:
    settings = get_settings()
    target = settings.project_dir / payload.filename
    if not target.exists():
        raise HTTPException(status_code=404, detail="Project file not found")

    with target.open("r", encoding="utf-8") as fp:
        raw = json.load(fp)

    project = ProjectPayload(**raw)

    session.exec(delete(Child))
    session.exec(delete(Family))
    session.exec(delete(Person))
    session.exec(delete(PageText))
    session.exec(delete(Source))
    session.commit()

    for source in project.sources:
        session.add(Source(**source.model_dump()))
    session.commit()
\n
    for page in project.pages:
        session.add(PageText(**page.model_dump()))
    session.commit()

    for person in project.persons:
        session.add(Person(**person.model_dump()))
    session.commit()

    for family in project.families:
        session.add(Family(**family.model_dump()))
    session.commit()

    for child in project.children:
        session.add(Child(**child.model_dump()))
    session.commit()

    return JSONResponse({"status": "opened", "filename": payload.filename})


def _timestamped_filename(stem: str, suffix: str) -> str:
    return f"{stem}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.{suffix}"


