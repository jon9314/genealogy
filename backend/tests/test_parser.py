from typing import Optional

import pytest
from sqlmodel import SQLModel, Session, create_engine, select

from app.core.models import Child, Family, Person, Source
from app.core.parser import parse_ocr_text


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'parser.db'}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


def _create_source(session: Session) -> Source:
    source = Source(name="descendancy.pdf", path="/tmp/descendancy.pdf")
    session.add(source)
    session.commit()
    return source


def _get_person(
    session: Session,
    *,
    given: str,
    surname: Optional[str] = None,
    birth_contains: Optional[str] = None,
    title: Optional[str] = None,
) -> Person:
    people = session.exec(select(Person)).all()
    matches = []
    for person in people:
        if person.given != given:
            continue
        if surname is not None:
            if not person.surname or person.surname.upper() != surname.upper():
                continue
        if title is not None and person.title != title:
            continue
        if birth_contains is not None:
            if not person.birth or birth_contains not in person.birth:
                continue
        matches.append(person)
    assert matches, f"No match for {given} {surname}"
    return matches[0]


def test_newcomb_chart_structure(session: Session):
    source = _create_source(session)
    sample = """
1-- Andrew NEWCOMB Lt.-117 (1640-1706)
sp-Sarah-118 (-1674)
2-- Simon NEWCOMB-1761 (1662)
2-- Andrew NEWCOMB-1762 (1664-1687)
2-- Simon NEWCOMB Lt.-115 (1665-1744)
sp-Deborah ?-116 (1664-1756)
3-- John NEWCOMB Deacon-1653 (1688-1765)
4-- Eddy NEWCOMB-1964
sp-Abigail ENGLISH-973 (1724)
""".strip()

    stats = parse_ocr_text(session, source_id=source.id, pages=[sample])

    people = session.exec(select(Person)).all()
    families = session.exec(select(Family)).all()
    children = session.exec(select(Child)).all()

    assert stats == {"people": 9, "families": len(families), "children": len(children)}

    andrew = _get_person(session, given="Andrew", surname="NEWCOMB", birth_contains="1640")
    assert andrew.gen == 1
    assert andrew.line_key
    assert andrew.title in {"Lt", "Lt."}

    sarah = _get_person(session, given="Sarah")
    assert sarah.approx is True
    andrew_family = next(
        fam for fam in families if {fam.husband_id, fam.wife_id} == {andrew.id, sarah.id}
    )
    assert andrew_family.line_key

    family_children = [
        session.get(Person, link.person_id)
        for link in children
        if link.family_id == andrew_family.id
    ]
    actual_children = {
        (child.given, child.birth, child.death)
        for child in family_children
    }
    assert actual_children == {
        ("Simon", "1662", None),
        ("Andrew", "1664", "1687"),
        ("Simon", "1665", "1744"),
    }

    simon_lt = _get_person(session, given="Simon", surname="NEWCOMB", birth_contains="1665")
    assert simon_lt.title in {"Lt", "Lt."}
    deborah = _get_person(session, given="Deborah")
    assert deborah.approx is True
    assert deborah.notes and "ID 116" in deborah.notes

    simon_family = next(
        fam for fam in families if {fam.husband_id, fam.wife_id} == {simon_lt.id, deborah.id}
    )
    assert simon_family.approx is True

    john = _get_person(session, given="John", surname="NEWCOMB", birth_contains="1688")
    john_link = next(
        link for link in children if link.family_id == simon_family.id and link.person_id == john.id
    )
    assert john.title == "Deacon"
    assert john.gen == 3
    assert john_link is not None

    eddy = _get_person(session, given="Eddy", surname="NEWCOMB")
    assert eddy.gen == 4

    abigail = _get_person(session, given="Abigail", surname="ENGLISH")
    assert abigail.birth == "1724"

    eddy_family = next(
        fam for fam in families if {fam.husband_id, fam.wife_id} == {eddy.id, abigail.id}
    )
    assert eddy_family.line_key


def test_spouse_attaches_to_child(session: Session):
    source = _create_source(session)
    sample = """
1-- George ROOT
    2-- Henry ROOT
    sp-Clara SMITH
    2-- Helen ROOT
""".strip()

    parse_ocr_text(session, source_id=source.id, pages=[sample])

    families = session.exec(select(Family)).all()

    henry = _get_person(session, given="Henry", surname="ROOT")
    clara = _get_person(session, given="Clara", surname="SMITH")

    couple_family = next(
        fam for fam in families if {fam.husband_id, fam.wife_id} == {henry.id, clara.id}
    )
    clara_families = [fam for fam in families if clara.id in {fam.husband_id, fam.wife_id}]
    assert clara_families == [couple_family]


def test_idempotent_parse_no_duplicates(session: Session):
    source = _create_source(session)
    sample = """
1-- Root Person
sp-Partner One
2-- Child Person
""".strip()

    parse_ocr_text(session, source_id=source.id, pages=[sample])
    first_people = session.exec(select(Person)).all()
    first_keys = {person.line_key for person in first_people}
    first_family_count = len(session.exec(select(Family)).all())
    first_child_count = len(session.exec(select(Child)).all())

    parse_ocr_text(session, source_id=source.id, pages=[sample])
    second_people = session.exec(select(Person)).all()

    assert {person.line_key for person in second_people} == first_keys
    assert len(second_people) == len(first_people)
    assert len(session.exec(select(Family)).all()) == first_family_count
    assert len(session.exec(select(Child)).all()) == first_child_count


def test_question_mark_marks_approx(session: Session):
    source = _create_source(session)
    sample = """
1-- Mystery DOE (? Johnson) (1790-?)
sp-Partner ?- (1800)
2-- Descendant DOE (? ) (abt 1825)
""".strip()

    parse_ocr_text(session, source_id=source.id, pages=[sample])

    people = session.exec(select(Person)).all()
    assert people
    for person in people:
        assert person.approx is True

    family = session.exec(select(Family)).one()
    assert family.approx is True

    child_link = session.exec(select(Child)).one()
    assert child_link.approx is True
