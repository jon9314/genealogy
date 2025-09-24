import io

import pytest
from fastapi.responses import JSONResponse
from sqlmodel import SQLModel, Session, create_engine, select

from app.api.parse import parse_source
from app.core.gedcom import export_gedcom
from app.core.models import Child, Family, PageText, Person, Source
from app.core.parser import parse_person_line, parse_spouse_line


@pytest.fixture
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_parse_person_line_extracts_chart_and_dates():
    parsed = parse_person_line("1-- Andrew NEWCOMB Lt.-117 (1640-1706)")
    assert parsed.gen == 1
    assert parsed.chart_id == "117"
    assert parsed.title == "Lt."
    assert parsed.birth == "1640"
    assert parsed.death == "1706"
    assert parsed.given == "Andrew"
    assert parsed.surname == "NEWCOMB"


def test_parse_spouse_line_assigns_generation():
    parsed = parse_spouse_line("sp-Sarah-118 (-1674)", current_gen=1)
    assert parsed.is_spouse is True
    assert parsed.gen == 1
    assert parsed.chart_id == "118"
    assert parsed.death == "1674"


def test_generation_linking_across_pages(session: Session):
    source = Source(name="bundle.pdf", path="/tmp/bundle.pdf", pages=2, ocr_done=True)
    session.add(source)
    session.commit()

    page1 = PageText(
        source_id=source.id,
        page_index=0,
        text="\n".join(
            [
                "1-- Andrew NEWCOMB Lt.-117 (1640-1706)",
                "sp-Sarah-118 (-1674)",
                "2-- Simon NEWCOMB-1761 (1662)",
                "2-- Andrew NEWCOMB-1762 (1664-1687)",
            ]
        ),
    )
    page2 = PageText(
        source_id=source.id,
        page_index=1,
        text="\n".join(
            [
                "2-- Simon NEWCOMB Lt.-115 (1665-1744)",
                "3-- John NEWCOMB Deacon-1653 (1688-1765)",
                "sp-Abigail ENGLISH-973 (1724)",
            ]
        ),
    )
    session.add(page1)
    session.add(page2)
    session.commit()

    response = parse_source(source.id, session=session)
    assert isinstance(response, JSONResponse)

    people = session.exec(select(Person)).all()
    assert len(people) == 7

    john = next(person for person in people if person.name.startswith("John NEWCOMB"))
    john_links = session.exec(select(Child).where(Child.person_id == john.id)).all()
    assert len(john_links) == 1
    john_family = session.get(Family, john_links[0].family_id)
    assert john_family is not None
    parent_ids = {john_family.husband_id, john_family.wife_id}
    simon = next(person for person in people if person.chart_id == "115")
    assert simon.id in parent_ids


def test_gedcom_snapshot(session: Session):
    source = Source(name="bundle.pdf", path="/tmp/bundle.pdf")
    session.add(source)
    session.commit()

    root = Person(name="Andrew NEWCOMB", gen=1, source_id=source.id)
    child = Person(name="John NEWCOMB", gen=2, source_id=source.id)
    session.add(root)
    session.add(child)
    session.commit()

    family = Family(husband_id=root.id)
    session.add(family)
    session.commit()

    session.add(Child(family_id=family.id, person_id=child.id, order_index=0))
    session.commit()

    buffer = io.StringIO()
    export_gedcom(session, buffer, "test.ged")
    data = buffer.getvalue()
    assert "0 HEAD" in data
    assert "1 SOUR" in data
    assert "0 @I" in data
    assert "0 TRLR" in data

