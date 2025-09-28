import pytest
from sqlmodel import SQLModel, Session, create_engine, select

from app.core.models import Child, Family, Person, Source
from app.core.parser import parse_ocr_text


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'parser.db'}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _create_source(session: Session) -> Source:
    source = Source(name="descendancy.pdf", path="/tmp/descendancy.pdf")
    session.add(source)
    session.commit()
    return source


def _fetch_people(session: Session):
    return session.exec(select(Person)).all()


def test_parse_chart_variants(session: Session):
    source = _create_source(session)

    text = """
1. Andrew Newcomb-1 (b. 1625, Devon; d. after 1686, Edgartown) m. Sarah Unknown (d. 1703)
   Children: 
   1) John (b. 1655) 
   2) Simon Newcomb (b. ca. 1657; d. 1729)
2) John Newcomb—2 married to Hannah Smith (m. 1680)
   Issue: - Mary (b. 1681) - Thomas (b. 1683, Boston, MA)
A) Simon Newcomb-3 wife: Elizabeth Brown
   - William (bapt. 1685)
   - Ann (bapt. 1687)
#4 Peter Newcomb sp: Jane Doe (d. after 1700)
    """.strip()

    stats = parse_ocr_text(session, source_id=source.id, pages=[text])
    assert stats["people"] >= 8
    assert stats["families"] >= 3
    assert stats["children"] >= 4

    people = _fetch_people(session)
    mary = next((p for p in people if p.given == "Mary"), None)
    assert mary is not None
    assert mary.surname == "Newcomb"
    assert mary.birth and "1681" in mary.birth

    thomas = next((p for p in people if p.given == "Thomas" and p.surname == "Newcomb"), None)
    assert thomas is not None
    assert "Boston" in (thomas.birth or "")

    families = session.exec(select(Family)).all()
    child_links = session.exec(select(Child)).all()
    assert len(child_links) >= 4

    john = next(p for p in people if p.given == "John" and p.surname == "Newcomb" and p.birth)
    hannah = next(p for p in people if p.given == "Hannah" and p.surname == "Smith")
    shared_family = next(
        f
        for f in families
        if {f.husband_id, f.wife_id} == {john.id, hannah.id}
    )
    john_children = [link for link in child_links if link.family_id == shared_family.id]
    assert any(session.get(Person, link.person_id).given == "Mary" for link in john_children)


def test_parse_is_idempotent(session: Session):
    source = _create_source(session)
    text = """
-1 John Doe (b. 1900)
  Children: - Jane (b. 1925)
    """.strip()

    parse_ocr_text(session, source_id=source.id, pages=[text])
    first_people = {person.id for person in _fetch_people(session)}

    parse_ocr_text(session, source_id=source.id, pages=[text])
    second_people = {person.id for person in _fetch_people(session)}

    assert first_people == second_people
    assert len(first_people) == 2

    families = session.exec(select(Family)).all()
    children = session.exec(select(Child)).all()
    assert len(families) == 1
    assert len(children) == 1


def test_single_person_line(session: Session):
    source = _create_source(session)
    text = "1. John Doe-1 (b. 1800; d. 1880)"

    stats = parse_ocr_text(session, source_id=source.id, pages=[text])
    assert stats["people"] == 1
    assert stats["families"] == 0
    assert stats["children"] == 0

    person = session.exec(select(Person)).one()
    assert person.given == "John"
    assert person.surname == "Doe"
    assert person.gen == 1
    assert person.birth == "1800"
    assert person.death == "1880"
    assert person.birth_year == 1800
    assert person.approx in (None, False)
    assert person.line_key is not None


def test_couple_with_equals_sign(session: Session):
    source = _create_source(session)
    text = "1. John Doe = Mary Smith"

    stats = parse_ocr_text(session, source_id=source.id, pages=[text])
    assert stats["people"] == 2
    assert stats["families"] == 1

    people = session.exec(select(Person)).all()
    john = next(p for p in people if p.given == "John")
    mary = next(p for p in people if p.given == "Mary")
    family = session.exec(select(Family)).one()
    assert {family.husband_id, family.wife_id} == {john.id, mary.id}
    assert family.line_key is not None


def test_children_multiple_generations(session: Session):
    source = _create_source(session)
    text = """
1. John Doe (b. 1800)
   Children: 1) William Doe (b. 1830)
2. William Doe (b. 1830)
   Children: - Charles Doe (b. 1860)
    """.strip()

    stats = parse_ocr_text(session, source_id=source.id, pages=[text])
    assert stats["people"] == 3
    assert stats["families"] >= 2
    assert stats["children"] >= 2

    people = {p.given: p for p in session.exec(select(Person)).all()}
    john = people["John"]
    william = people["William"]
    charles = people["Charles"]
    assert john.gen == 1
    assert william.gen == 2
    assert charles.gen == 3

    families = session.exec(select(Family)).all()
    children = session.exec(select(Child)).all()
    john_family = next(f for f in families if {f.husband_id, f.wife_id} & {john.id})
    william_links = [link for link in children if link.family_id == john_family.id]
    assert any(session.get(Person, link.person_id).id == william.id for link in william_links)

    william_family = next(f for f in families if {f.husband_id, f.wife_id} & {william.id})
    charles_links = [link for link in children if link.family_id == william_family.id]
    assert any(session.get(Person, link.person_id).id == charles.id for link in charles_links)


def test_approximate_dates_marked(session: Session):
    source = _create_source(session)
    text = """
1. Jane Roe (b. ~1840; d. abt 1900)
   = John Roe (b. ca. 1835)
   Children: - Baby Roe (b. about 1865)
    """.strip()

    parse_ocr_text(session, source_id=source.id, pages=[text])

    people = {p.given: p for p in session.exec(select(Person)).all()}
    jane = people["Jane"]
    john = people["John"]
    baby = people["Baby"]
    assert jane.approx is True
    assert john.approx is True
    assert baby.approx is True

    family = session.exec(select(Family)).one()
    assert family.approx is True

    child_link = session.exec(select(Child)).one()
    assert child_link.approx is True


def test_missing_ids_and_years(session: Session):
    source = _create_source(session)
    text = """
1. Henry Doe- (d. 1900)
   = Mary Roe- (b. )
   Children: - James Doe-3
    """.strip()

    stats = parse_ocr_text(session, source_id=source.id, pages=[text])
    assert stats["people"] == 3

    people = {p.given: p for p in session.exec(select(Person)).all()}
    henry = people["Henry"]
    mary = people["Mary"]
    james = people["James"]

    assert henry.birth is None
    assert henry.death == "1900"
    assert mary.birth is None
    assert james.birth is None
    assert james.birth_year is None
    assert james.line_key is not None
