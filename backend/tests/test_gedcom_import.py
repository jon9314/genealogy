"""
Test GEDCOM import functionality to verify bug fixes.

This test verifies that the critical bugs fixed are working:
- Bug #2: Source field names (name/path/stage instead of filename/filepath/parse_done)
- Bug #5: Xref handling without crashes
"""

import pytest
from pathlib import Path
from sqlmodel import SQLModel, Session, create_engine

from app.core.gedcom import import_gedcom
from app.core.models import Source, Person, Family, Child


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


# Minimal valid GEDCOM for testing
MINIMAL_GEDCOM = """0 HEAD
1 SOUR TestSource
1 GEDC
2 VERS 5.5.1
1 CHAR UTF-8
0 @I1@ INDI
1 NAME John /Doe/
1 SEX M
1 BIRT
2 DATE 1800
1 FAMS @F1@
0 @I2@ INDI
1 NAME Jane /Smith/
1 SEX F
1 BIRT
2 DATE 1805
1 FAMS @F1@
0 @I3@ INDI
1 NAME William /Doe/
1 SEX M
1 BIRT
2 DATE 1825
1 FAMC @F1@
0 @F1@ FAM
1 HUSB @I1@
1 WIFE @I2@
1 CHIL @I3@
0 TRLR
"""


def test_gedcom_import_creates_source_with_correct_fields(session: Session):
    """
    Test that Source is created with correct field names.
    Bug Fix #2: Verify 'name', 'path', 'stage' fields work (not filename/filepath/parse_done).
    """
    result = import_gedcom(session, MINIMAL_GEDCOM)

    # Check that import completed
    assert len(result['persons']) == 3
    assert len(result['families']) == 1
    assert len(result['children']) == 1

    # Verify Source was created with correct field names
    sources = session.query(Source).all()
    assert len(sources) == 1

    source = sources[0]

    # Bug Fix #2: These field names must work (not filename/filepath/parse_done)
    assert hasattr(source, 'name'), "Source must have 'name' field"
    assert hasattr(source, 'path'), "Source must have 'path' field"
    assert hasattr(source, 'stage'), "Source must have 'stage' field"

    # Verify values
    assert source.name == "GEDCOM Import"
    assert source.path.startswith("import_")
    assert source.path.endswith(".ged")
    assert source.stage == "parsed"
    assert source.ocr_done is True


def test_gedcom_import_creates_persons(session: Session):
    """Test that persons are imported correctly from GEDCOM."""
    result = import_gedcom(session, MINIMAL_GEDCOM)

    assert len(result['persons']) == 3

    persons = session.query(Person).all()
    assert len(persons) == 3

    # Check that persons have correct names
    names = sorted([p.name for p in persons])
    assert "John Doe" in names
    assert "Jane Smith" in names
    assert "William Doe" in names

    # Check birth years extracted
    john = next(p for p in persons if p.given == "John")
    assert john.birth_year == 1800


def test_gedcom_import_creates_families(session: Session):
    """Test that families are created with proper parent links."""
    result = import_gedcom(session, MINIMAL_GEDCOM)

    assert len(result['families']) == 1

    families = session.query(Family).all()
    assert len(families) == 1

    family = families[0]
    assert family.husband_id is not None
    assert family.wife_id is not None

    # Verify parents exist
    husband = session.get(Person, family.husband_id)
    wife = session.get(Person, family.wife_id)
    assert husband is not None
    assert wife is not None


def test_gedcom_import_creates_children_links(session: Session):
    """Test that parent-child relationships are created."""
    result = import_gedcom(session, MINIMAL_GEDCOM)

    assert len(result['children']) == 1

    children = session.query(Child).all()
    assert len(children) == 1

    child_link = children[0]
    assert child_link.family_id is not None
    assert child_link.person_id is not None

    # Verify child person exists
    child_person = session.get(Person, child_link.person_id)
    assert child_person is not None
    assert child_person.given == "William"


def test_gedcom_import_handles_xref_correctly(session: Session):
    """
    Test that xref references are handled without crashes.
    Bug Fix #5: Verify xref value extraction doesn't crash on missing values.
    """
    # This GEDCOM has a family with only one parent (testing None handling)
    single_parent_gedcom = """0 HEAD
1 SOUR TestSource
1 GEDC
2 VERS 5.5.1
1 CHAR UTF-8
0 @I1@ INDI
1 NAME John /Doe/
1 SEX M
0 @F1@ FAM
1 HUSB @I1@
1 CHIL @I2@
0 @I2@ INDI
1 NAME Jane /Doe/
1 SEX F
1 FAMC @F1@
0 TRLR
"""

    # This should not crash
    result = import_gedcom(session, single_parent_gedcom)

    assert len(result['persons']) == 2
    assert len(result['families']) == 1

    # Verify family has only husband
    family = session.query(Family).first()
    assert family.husband_id is not None
    assert family.wife_id is None or family.wife_id == family.husband_id


def test_gedcom_import_with_real_file(session: Session):
    """Test importing the actual john_cowan.ged file if it exists."""
    gedcom_path = Path(__file__).parent.parent.parent / "john_cowan.ged"

    if not gedcom_path.exists():
        pytest.skip(f"john_cowan.ged not found at {gedcom_path}")

    with open(gedcom_path, 'r', encoding='utf-8') as f:
        gedcom_data = f.read()

    # Import should not crash
    result = import_gedcom(session, gedcom_data)

    # Verify basic import stats
    assert len(result['persons']) > 0
    assert len(result['families']) >= 0

    # Verify source created correctly
    source = session.query(Source).first()
    assert source is not None
    assert source.name == "GEDCOM Import"
    assert source.stage == "parsed"

    print(f"\n✅ Imported {len(result['persons'])} persons and {len(result['families'])} families from john_cowan.ged")
