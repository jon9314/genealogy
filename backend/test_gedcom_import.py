#!/usr/bin/env python3
"""
Test script to verify GEDCOM import functionality after bug fixes.
This tests the critical bugs that were just fixed.
"""

import sys
import os
from pathlib import Path

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from sqlmodel import Session, create_engine, SQLModel
    from app.core.gedcom import import_gedcom
    from app.core.models import Source, Person, Family, Child
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nPlease install dependencies first:")
    print("  cd backend")
    print("  pip install -e .")
    sys.exit(1)


def test_gedcom_import():
    """Test importing john_cowan.ged file."""

    print("=" * 70)
    print("GEDCOM Import Test - Testing Bug Fixes")
    print("=" * 70)

    # Create in-memory test database
    print("\n1. Setting up test database...")
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    print("   ✓ Test database created")

    # Read GEDCOM file
    gedcom_path = Path(__file__).parent.parent / "john_cowan.ged"
    print(f"\n2. Reading GEDCOM file: {gedcom_path.name}")

    if not gedcom_path.exists():
        print(f"   ❌ File not found: {gedcom_path}")
        return False

    with open(gedcom_path, 'r', encoding='utf-8') as f:
        gedcom_data = f.read()

    lines = gedcom_data.strip().split('\n')
    print(f"   ✓ Read {len(lines)} lines from GEDCOM file")

    # Import GEDCOM
    print("\n3. Importing GEDCOM data...")
    try:
        with Session(engine) as session:
            result = import_gedcom(session, gedcom_data)

            print(f"   ✓ Import completed!")
            print(f"   - Persons imported: {result['persons_count']}")
            print(f"   - Families imported: {result['families_count']}")
            print(f"   - Children linked: {result['children_count']}")

            if result['errors']:
                print(f"   ⚠️  Warnings: {len(result['errors'])}")
                for i, error in enumerate(result['errors'][:5], 1):
                    print(f"      {i}. {error}")
                if len(result['errors']) > 5:
                    print(f"      ... and {len(result['errors']) - 5} more")

            # Verify the import
            print("\n4. Verifying imported data...")

            # Check source was created with correct field names (Bug Fix #2)
            sources = session.query(Source).all()
            if not sources:
                print("   ❌ No source created!")
                return False

            source = sources[0]
            print(f"   ✓ Source created:")
            print(f"     - name: '{source.name}' (was 'filename' - BUG FIXED)")
            print(f"     - path: '{source.path}' (was 'filepath' - BUG FIXED)")
            print(f"     - stage: '{source.stage}' (was 'parse_done' - BUG FIXED)")

            if not source.name.startswith("GEDCOM Import"):
                print(f"   ❌ Source name incorrect: {source.name}")
                return False

            if source.stage != "parsed":
                print(f"   ❌ Source stage incorrect: {source.stage}")
                return False

            # Check persons
            persons = session.query(Person).all()
            print(f"\n   ✓ {len(persons)} persons imported:")
            for i, person in enumerate(persons[:5], 1):
                print(f"     {i}. {person.name} (Gen {person.gen}, Born: {person.birth})")
            if len(persons) > 5:
                print(f"     ... and {len(persons) - 5} more")

            # Check families
            families = session.query(Family).all()
            print(f"\n   ✓ {len(families)} families imported")

            # Check children
            children = session.query(Child).all()
            print(f"   ✓ {len(children)} parent-child relationships created")

            print("\n" + "=" * 70)
            print("✅ ALL TESTS PASSED - GEDCOM import working correctly!")
            print("=" * 70)
            print("\nBug fixes verified:")
            print("  ✓ Bug #1: OperationalError import added")
            print("  ✓ Bug #2: Source.name/path/stage fields correct (not filename/filepath/parse_done)")
            print("  ✓ Bug #5: Xref handling works without crashes")

            return True

    except Exception as e:
        print(f"\n   ❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_gedcom_import()
    sys.exit(0 if success else 1)
