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


def validate_gedcom(gedcom: str) -> list[str]:
    from gedcom_validator import GedcomValidator

    validator = GedcomValidator()
    errors, _ = validator.validate(gedcom)
    return [str(e) for e in errors]


def import_gedcom(session: Session, gedcom_data: str) -> dict:
    from ged4py import GedcomReader

    reader = GedcomReader(gedcom_data)
    imported_persons = []
    imported_families = []

    for record in reader.records0():
        if record.tag == "INDI":
            name_record = record.sub_record("NAME")
            name = name_record.value if name_record else "Unknown"
            given = None
            surname = None
            if name_record and "/" in name_record.value:
                parts = name_record.value.split("/")
                given = parts[0].strip() if parts[0].strip() else None
                surname = parts[1].strip() if parts[1].strip() else None

            birth_record = record.sub_record("BIRT")
            birth_date = birth_record.sub_record("DATE").value if birth_record and birth_record.sub_record("DATE") else None

            death_record = record.sub_record("DEAT")
            death_date = death_record.sub_record("DATE").value if death_record and death_record.sub_record("DATE") else None

            sex_record = record.sub_record("SEX")
            sex = sex_record.value if sex_record else None

            title_record = record.sub_record("TITL")
            title = title_record.value if title_record else None

            notes_records = record.sub_records("NOTE")
            notes = "\n".join([n.value for n in notes_records]) if notes_records else None

            # Simple merging logic: check for existing person by name and birth date
            existing_person = session.exec(
                select(Person).where(
                    Person.name == name,
                    Person.birth == birth_date
                )
            ).first()

            if existing_person:
                # Update existing person
                if not existing_person.given and given:
                    existing_person.given = given
                if not existing_person.surname and surname:
                    existing_person.surname = surname
                if not existing_person.death and death_date:
                    existing_person.death = death_date
                if not existing_person.sex and sex:
                    existing_person.sex = sex
                if not existing_person.title and title:
                    existing_person.title = title
                if not existing_person.notes and notes:
                    existing_person.notes = notes
                session.add(existing_person)
                imported_persons.append({"id": existing_person.id, "action": "updated"})
            else:
                # Create new person
                new_person = Person(
                    name=name,
                    given=given,
                    surname=surname,
                    birth=birth_date,
                    death=death_date,
                    sex=sex,
                    title=title,
                    notes=notes,
                    gen=0, # Default generation, can be updated later
                )
                session.add(new_person)
                session.flush() # To get the ID
                imported_persons.append({"id": new_person.id, "action": "created"})

        elif record.tag == "FAM":
            husband_xref = record.sub_record("HUSB").value if record.sub_record("HUSB") else None
            wife_xref = record.sub_record("WIFE").value if record.sub_record("WIFE") else None
            
            # Assuming xrefs are like @I123@
            husband_id = int(husband_xref[2:-1]) if husband_xref else None
            wife_id = int(wife_xref[2:-1]) if wife_xref else None

            # Simple merging logic for families
            existing_family = None
            if husband_id and wife_id:
                existing_family = session.exec(
                    select(Family).where(
                        (Family.husband_id == husband_id) & (Family.wife_id == wife_id) |
                        (Family.husband_id == wife_id) & (Family.wife_id == husband_id)
                    )
                ).first()
            elif husband_id:
                existing_family = session.exec(
                    select(Family).where(Family.husband_id == husband_id, Family.is_single_parent == True)
                ).first()
            elif wife_id:
                existing_family = session.exec(
                    select(Family).where(Family.wife_id == wife_id, Family.is_single_parent == True)
                ).first()

            if existing_family:
                imported_families.append({"id": existing_family.id, "action": "updated"})
            else:
                new_family = Family(
                    husband_id=husband_id,
                    wife_id=wife_id,
                    is_single_parent=not (husband_id and wife_id)
                )
                session.add(new_family)
                session.flush()
                imported_families.append({"id": new_family.id, "action": "created"})

            # TODO: Handle children linking

    session.commit()
    # TODO: Implement proper rollback mechanism if user doesn't like the result
    return {"persons": imported_persons, "families": imported_families}
