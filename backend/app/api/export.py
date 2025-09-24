from __future__ import annotations

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from ..core.gedcom import export_gedcom
from ..core.models import Person
from ..db import get_session

router = APIRouter(prefix="/export", tags=["export"])


def _timestamped_filename(stem: str, suffix: str) -> str:
    return f"{stem}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.{suffix}"


@router.post("/gedcom")
def export_gedcom_file(session: Session = Depends(get_session)) -> StreamingResponse:
    filename = _timestamped_filename("genealogy", "ged")
    buffer = io.StringIO()
    export_gedcom(session, buffer, filename)
    data = buffer.getvalue().encode("utf-8")
    return StreamingResponse(
        iter([data]),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/csv")
def export_csv_file(session: Session = Depends(get_session)) -> StreamingResponse:
    filename = _timestamped_filename("genealogy", "csv")
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    header = [
        "id",
        "chart_id",
        "gen",
        "name",
        "given",
        "surname",
        "birth",
        "death",
        "sex",
        "title",
        "notes",
        "source_id",
        "page_index",
        "line_index",
    ]
    writer.writerow(header)
    people = session.exec(select(Person).order_by(Person.gen, Person.id)).all()
    for person in people:
        writer.writerow(
            [
                person.id,
                person.chart_id,
                person.gen,
                person.name,
                person.given,
                person.surname,
                person.birth,
                person.death,
                person.sex,
                person.title,
                person.notes,
                person.source_id,
                person.page_index,
                person.line_index,
            ]
        )
    data = buffer.getvalue().encode("utf-8")
    return StreamingResponse(
        iter([data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


