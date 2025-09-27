import pytest
from sqlmodel import SQLModel, Session, create_engine

from app.core.models import Child, Family, Person, Source


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'model.db'}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_person_upsert_deduplicates_by_line_key(session: Session):
    source = Source(name="chart.pdf", path="/tmp/chart.pdf")
    session.add(source)
    session.commit()

    vitals = {"birth": "1650", "death": "1700"}
    person = Person.upsert_from_parse(
        session,
        source.id,
        "John",
        "Newcomb",
        vitals=vitals,
        line_key="a1",
        gen=1,
        name="John Newcomb",
    )
    session.commit()

    same = Person.upsert_from_parse(session, source.id, "John", "Newcomb", vitals, line_key="a1")
    session.commit()

    assert person.id == same.id
    assert session.get(Person, person.id).line_key == "a1"


def test_person_upsert_soft_dedupe(session: Session):
    source = Source(name="chart.pdf", path="/tmp/chart.pdf")
    session.add(source)
    session.commit()

    vitals = {"birth": {"raw": "abt 1700", "year": 1700}}
    first = Person.upsert_from_parse(session, source.id, "Andrew", "Newcomb", vitals, line_key="row-1")
    session.commit()

    second = Person.upsert_from_parse(
        session,
        source.id,
        "Andrw",
        "Newcomb",
        vitals={"birth": "1700"},
        line_key=None,
        gen=1,
        name="Andrw Newcomb",
    )
    session.commit()

    assert first.id == second.id
    stored = session.get(Person, first.id)
    assert stored.birth_year == 1700


def test_family_helpers(session: Session):
    source = Source(name="chart.pdf", path="/tmp/chart.pdf")
    session.add(source)
    session.commit()

    alice = Person(source_id=source.id, name="Alice Doe", gen=1)
    bob = Person(source_id=source.id, name="Bob Doe", gen=1)
    session.add(alice)
    session.add(bob)
    session.commit()

    fam1 = Family.upsert_couple(session, source.id, alice.id, bob.id)
    fam2 = Family.upsert_couple(session, source.id, bob.id, alice.id)
    session.commit()

    assert fam1.id == fam2.id

    child = Person(source_id=source.id, name="Charlie Doe", gen=2)
    session.add(child)
    session.commit()

    link1 = Child.link(session, fam1.id, child.id)
    link2 = Child.link(session, fam1.id, child.id)
    session.commit()

    assert link1.id == link2.id


def test_single_parent_family(session: Session):
    source = Source(name="chart.pdf", path="/tmp/chart.pdf")
    session.add(source)
    session.commit()

    parent = Person(source_id=source.id, name="Jane Doe", gen=1, sex="F")
    session.add(parent)
    session.commit()

    fam = Family.ensure_for_single_parent(session, source.id, parent.id)
    session.commit()

    assert fam.wife_id == parent.id
    again = Family.ensure_for_single_parent(session, source.id, parent.id)
    assert fam.id == again.id
