from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from io import TextIOBase
from typing import Iterable

from sqlmodel import Session, select

try:  # pragma: no cover - import guard
    from ged4py import GedcomWriter  # type: ignore
except Exception:  # pragma: no cover - fallback if library unavailable at runtime
    GedcomWriter = None

from .models import Child, Family, Person
from .settings import get_settings


def _format_name(person: Person) -> str:
    if person.surname:
        given = person.given or person.name
        return f"{given} /{person.surname}/"
    return person.name


def wrap_gedcom_text(text: str, width: int = 240) -> Iterable[str]:
    start = 0
    while start < len(text):
        yield text[start : start + width]
        start += width


def _export_with_library(
    session: Session,
    stream: TextIOBase,
    filename: str,
) -> bool:
    if GedcomWriter is None:
        return False
    settings = get_settings()
    persons: list[Person] = list(session.exec(select(Person)).all())
    families: list[Family] = list(session.exec(select(Family)).all())
    children: list[Child] = list(session.exec(select(Child)).all())

    children_by_family: dict[int, list[Child]] = defaultdict(list)
    for child in children:
        children_by_family[child.family_id].append(child)
    for ordered_children in children_by_family.values():
        ordered_children.sort(key=lambda item: item.order_index)

    person_xref = {person.id: f"I{person.id}" for person in persons}
    family_xref = {family.id: f"F{family.id}" for family in families}

    with GedcomWriter(stream, encoding="utf-8", version="5.5.1") as writer:  # type: ignore[operator]
        header = writer.header()
        header.add_tag("SOUR", settings.project_name)
        header.add_tag("DATE", datetime.utcnow().strftime("%d %b %Y"))
        header.add_tag("FILE", filename)

        for person in persons:
            indi = writer.add_record("INDI", xref=person_xref[person.id])
            indi.add_tag("NAME", _format_name(person))
            if person.sex in {"M", "F"}:
                indi.add_tag("SEX", person.sex)
            if person.birth:
                indi.add_tag("BIRT").add_tag("DATE", person.birth)
            if person.death:
                indi.add_tag("DEAT").add_tag("DATE", person.death)
            if person.title:
                indi.add_tag("TITL", person.title)
            if person.notes:
                for chunk in wrap_gedcom_text(person.notes):
                    indi.add_tag("NOTE", chunk)

        for family in families:
            fam = writer.add_record("FAM", xref=family_xref[family.id])
            if family.husband_id and family.husband_id in person_xref:
                fam.add_tag("HUSB", person_xref[family.husband_id])
            if family.wife_id and family.wife_id in person_xref:
                fam.add_tag("WIFE", person_xref[family.wife_id])
            for child in children_by_family.get(family.id, []):
                if child.person_id in person_xref:
                    fam.add_tag("CHIL", person_xref[child.person_id])
    return True


def _manual_export(session: Session, stream: TextIOBase, filename: str) -> None:
    settings = get_settings()
    persons: list[Person] = list(session.exec(select(Person)).all())
    families: list[Family] = list(session.exec(select(Family)).all())
    children: list[Child] = list(session.exec(select(Child)).all())

    children_by_family: dict[int, list[Child]] = defaultdict(list)
    for child in children:
        children_by_family[child.family_id].append(child)
    for ordered_children in children_by_family.values():
        ordered_children.sort(key=lambda item: item.order_index)

    stream.write("0 HEAD\n")
    stream.write(f"1 SOUR {settings.project_name}\n")
    stream.write(f"1 DATE {datetime.utcnow().strftime('%d %b %Y')}\n")
    stream.write(f"1 FILE {filename}\n")

    for person in persons:
        stream.write(f"0 @I{person.id}@ INDI\n")
        stream.write(f"1 NAME {_format_name(person)}\n")
        if person.sex in {"M", "F"}:
            stream.write(f"1 SEX {person.sex}\n")
        if person.birth:
            stream.write("1 BIRT\n")
            stream.write(f"2 DATE {person.birth}\n")
        if person.death:
            stream.write("1 DEAT\n")
            stream.write(f"2 DATE {person.death}\n")
        if person.title:
            stream.write(f"1 TITL {person.title}\n")
        if person.notes:
            for chunk in wrap_gedcom_text(person.notes):
                stream.write(f"1 NOTE {chunk}\n")

    for family in families:
        stream.write(f"0 @F{family.id}@ FAM\n")
        if family.husband_id:
            stream.write(f"1 HUSB @I{family.husband_id}@\n")
        if family.wife_id:
            stream.write(f"1 WIFE @I{family.wife_id}@\n")
        for child in children_by_family.get(family.id, []):
            stream.write(f"1 CHIL @I{child.person_id}@\n")

    stream.write("0 TRLR\n")


def export_gedcom(session: Session, stream: TextIOBase, filename: str) -> None:
    if not _export_with_library(session, stream, filename):
        _manual_export(session, stream, filename)
