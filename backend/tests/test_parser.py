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
