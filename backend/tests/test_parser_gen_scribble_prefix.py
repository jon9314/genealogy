import pytest
from sqlmodel import SQLModel, Session, create_engine, select

from app.core.models import Person, Source
from app.core.parser import parse_ocr_text


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'parser_gen.db'}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


def _create_source(session: Session) -> Source:
    source = Source(name="scribble.pdf", path="/tmp/scribble.pdf")
    session.add(source)
    session.commit()
    return source


def test_generation_with_scribble_prefix(session: Session):
    source = _create_source(session)
    sample = """
x 1-- Andrew NEWCOMB (1640-1706)
sp-Sarah (?-?)
2-- Simon NEWCOMB (1662)
""".strip()

    parse_ocr_text(session, source_id=source.id, pages=[sample])

    people = session.exec(select(Person)).all()
    assert len(people) == 3

    andrew = next(person for person in people if person.given == "Andrew")
    assert andrew.gen == 1

    sarah = next(person for person in people if person.given == "Sarah")
    assert sarah.gen == 1

    simon = next(person for person in people if person.given == "Simon")
    assert simon.gen == 2
