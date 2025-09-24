from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import Session, delete, select

from ..core.models import Child, Family, PageText, Person, Source
from ..core.parser import ParseError, parse_person_line, parse_spouse_line
from ..db import get_session

router = APIRouter(prefix="/parse", tags=["parse"])


@router.post("/{source_id}")
def parse_source(source_id: int, session: Session = Depends(get_session)) -> JSONResponse:
    source = session.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    page_texts = session.exec(
        select(PageText).where(PageText.source_id == source_id).order_by(PageText.page_index)
    ).all()
    if not page_texts:
        raise HTTPException(status_code=400, detail="OCR has not been run for this source")

    existing_people = session.exec(select(Person).where(Person.source_id == source_id)).all()
    existing_ids = [person.id for person in existing_people if person.id]
    if existing_ids:
        session.exec(delete(Child).where(Child.person_id.in_(existing_ids)))
    session.exec(delete(Person).where(Person.source_id == source_id))
    session.commit()

    last_at_gen: Dict[int, Person] = {}
    active_family: Dict[int, Family] = {}
    families_for_person: Dict[int, List[Family]] = defaultdict(list)
    child_counters: Dict[int, int] = defaultdict(int)
    current_person: Optional[Person] = None

    people_created = 0
    families_created = 0
    flagged_lines: List[str] = []

    def ensure_family(person: Person) -> Family:
        nonlocal families_created
        family = active_family.get(person.id)
        if family is None:
            family = Family()
            if person.sex == "F":
                family.wife_id = person.id
            else:
                family.husband_id = person.id
            session.add(family)
            session.flush()
            active_family[person.id] = family
            families_for_person[person.id].append(family)
            families_created += 1
        return family

    for page in page_texts:
        for idx, raw_line in enumerate(page.text.splitlines()):
            cleaned = raw_line.strip()
            if not cleaned:
                continue

            if current_person is not None and cleaned.lower().startswith("sp-"):
                try:
                    parsed = parse_spouse_line(cleaned, current_person.gen)
                except ParseError:
                    flagged_lines.append(cleaned)
                    continue
                spouse = Person(
                    name=parsed.name,
                    gen=parsed.gen,
                    chart_id=parsed.chart_id,
                    birth=parsed.birth,
                    death=parsed.death,
                    title=parsed.title,
                    given=parsed.given,
                    surname=parsed.surname,
                    notes=parsed.raw,
                    source_id=source_id,
                    page_index=page.page_index,
                    line_index=idx,
                )
                session.add(spouse)
                session.flush()
                people_created += 1

                family = ensure_family(current_person)
                primary_slot = "husband_id"
                spouse_slot = "wife_id"
                if current_person.sex == "F":
                    primary_slot = "wife_id"
                    spouse_slot = "husband_id"
                elif current_person.sex not in {"M", "F"}:
                    # Choose a primary slot that either references this person or is empty
                    if getattr(family, primary_slot) not in (None, current_person.id):
                        primary_slot = "wife_id"
                        spouse_slot = "husband_id"

                if getattr(family, primary_slot) not in (None, current_person.id):
                    family = Family()
                    setattr(family, primary_slot, current_person.id)
                    session.add(family)
                    session.flush()
                    active_family[current_person.id] = family
                    families_for_person[current_person.id].append(family)
                    families_created += 1

                setattr(family, primary_slot, current_person.id)
                existing_spouse_id = getattr(family, spouse_slot)
                if existing_spouse_id and existing_spouse_id != spouse.id:
                    family = Family()
                    setattr(family, primary_slot, current_person.id)
                    session.add(family)
                    session.flush()
                    active_family[current_person.id] = family
                    families_for_person[current_person.id].append(family)
                    families_created += 1
                setattr(family, spouse_slot, spouse.id)
                session.add(family)
                continue

            try:
                parsed = parse_person_line(cleaned)
            except ParseError:
                flagged_lines.append(cleaned)
                continue

            person = Person(
                name=parsed.name,
                gen=parsed.gen,
                chart_id=parsed.chart_id,
                birth=parsed.birth,
                death=parsed.death,
                title=parsed.title,
                given=parsed.given,
                surname=parsed.surname,
                notes=parsed.raw,
                source_id=source_id,
                page_index=page.page_index,
                line_index=idx,
            )
            session.add(person)
            session.flush()
            people_created += 1

            parent = last_at_gen.get(parsed.gen - 1)
            if parent:
                parent_family = ensure_family(parent)
                order_index = child_counters[parent_family.id]
                child_counters[parent_family.id] += 1
                child = Child(
                    family_id=parent_family.id,
                    person_id=person.id,
                    order_index=order_index,
                )
                session.add(child)

            last_at_gen[parsed.gen] = person
            for level in list(last_at_gen.keys()):
                if level > parsed.gen:
                    last_at_gen.pop(level, None)

            current_person = person

    session.commit()
    family_total = len(session.exec(select(Family)).all())
    return JSONResponse(
        {
            "people": people_created,
            "families": family_total,
            "flagged_lines": flagged_lines,
        }
    )
