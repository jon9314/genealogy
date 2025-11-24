#!/usr/bin/env python3
"""Test parsing with OpenRouter LLM using existing OCR'd PDF."""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Load .env file
from dotenv import load_dotenv
load_dotenv()

from app.db import init_db, get_session
from app.core.models import Source, PageText, Person, Family
from app.core.parser import parse_ocr_text
from app.core.settings import get_settings
from sqlmodel import select
import pytesseract
from pypdf import PdfReader


def main():
    """Test parsing with existing OCR'd PDF."""
    print("=" * 80)
    print("Testing Parsing with OpenRouter LLM")
    print("=" * 80)

    # Initialize database
    init_db()

    # Get settings
    settings = get_settings()
    print(f"\nLLM Provider: {settings.llm_provider}")
    if settings.llm_provider == "openrouter":
        print(f"Parse Model: {settings.openrouter_parse_model}")
        print(f"Context Parse Enabled: {settings.openrouter_use_context_parse}")

    # Use existing OCR'd PDF
    ocr_pdf = Path("data/ocr/75f18b9361ff4032a97750436f45c6aa-andrew_newcomb_descendace-ocr.pdf")

    if not ocr_pdf.exists():
        print(f"\n[ERROR] OCR PDF not found: {ocr_pdf}")
        return 1

    print(f"\nUsing OCR'd PDF: {ocr_pdf.name}")

    # Extract text from PDF
    print("\n" + "-" * 80)
    print("Extracting text from OCR'd PDF")
    print("-" * 80)

    reader = PdfReader(str(ocr_pdf))
    page_texts = []

    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        page_texts.append(text)
        print(f"  Page {page_num + 1}: {len(text)} characters")

    total_chars = sum(len(text) for text in page_texts)
    print(f"\nTotal text extracted: {total_chars} characters from {len(page_texts)} pages")

    if page_texts[0]:
        sample = page_texts[0][:300].replace('\n', ' ')
        print(f"\nSample text (page 1):\n  {sample}...")

    # Create source record
    session = next(get_session())

    source = Source(
        name="andrew_newcomb_descendace.pdf",
        path=str(ocr_pdf.absolute()),
        pages=len(page_texts),
        ocr_done=True,
        stage="ocr_done"
    )
    session.add(source)
    session.commit()
    session.refresh(source)

    print(f"\nCreated source (ID: {source.id})")

    # Save page texts to database
    for index, text in enumerate(page_texts):
        page = PageText(source_id=source.id, page_index=index, text=text)
        session.add(page)

    session.commit()

    # Step 2: Parse with OpenRouter LLM
    print("\n" + "-" * 80)
    print("Parsing OCR text with OpenRouter LLM")
    print("-" * 80)

    try:
        stats = parse_ocr_text(
            session,
            source_id=source.id,
            pages=page_texts
        )

        print("\n[OK] Parsing completed successfully")
        print(f"\nParsing Statistics:")
        print(f"  Persons created: {stats.get('persons_created', 0)}")
        print(f"  Families created: {stats.get('families_created', 0)}")
        print(f"  Children linked: {stats.get('children_created', 0)}")

        if 'llm_stats' in stats:
            llm_stats = stats['llm_stats']
            print(f"\nLLM Usage:")
            print(f"  Total attempts: {llm_stats.get('total_attempts', 0)}")
            print(f"  Successful parses: {llm_stats.get('successful_parses', 0)}")
            print(f"  Failed parses: {llm_stats.get('failed_parses', 0)}")
            print(f"  Success rate: {llm_stats.get('success_rate', 0)}%")
            print(f"  Multi-person splits: {llm_stats.get('multi_person_splits', 0)}")

    except Exception as e:
        print(f"[ERROR] Parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Step 3: Review Results
    print("\n" + "-" * 80)
    print("Reviewing Parsed Data")
    print("-" * 80)

    persons = session.exec(
        select(Person).where(Person.source_id == source.id)
    ).all()

    families = session.exec(
        select(Family).where(Family.source_id == source.id)
    ).all()

    print(f"\nDatabase Records:")
    print(f"  Total persons: {len(persons)}")
    print(f"  Total families: {len(families)}")

    # Group by generation
    by_generation = {}
    for person in persons:
        gen = person.gen or 0
        if gen not in by_generation:
            by_generation[gen] = []
        by_generation[gen].append(person)

    print(f"\nPersons by Generation:")
    for gen in sorted(by_generation.keys()):
        people = by_generation[gen]
        print(f"  Generation {gen}: {len(people)} persons")

    # Show sample persons
    print(f"\nSample Persons (first 15):")
    print("-" * 80)
    for i, person in enumerate(persons[:15], 1):
        birth = f"{person.birth_year}" if person.birth_year else "?"
        death = f"{person.death_year if hasattr(person, 'death_year') else '?'}"
        approx = " (approx)" if person.approx else ""
        print(f"{i:2}. Gen {person.gen}: {person.name} ({birth}-{death}){approx}")

    # Data quality checks
    print("\n" + "-" * 80)
    print("Data Quality Analysis")
    print("-" * 80)

    persons_with_birth = sum(1 for p in persons if p.birth_year)
    persons_approx = sum(1 for p in persons if p.approx)

    print(f"\nDate Coverage:")
    print(f"  Persons with birth year: {persons_with_birth}/{len(persons)} ({persons_with_birth/len(persons)*100:.1f}%)")
    print(f"  Approximate data flagged: {persons_approx}/{len(persons)} ({persons_approx/len(persons)*100:.1f}%)")

    # Check for potential duplicates
    names = {}
    for person in persons:
        normalized = person.name.lower().strip()
        if normalized in names:
            names[normalized].append(person)
        else:
            names[normalized] = [person]

    duplicates = {name: people for name, people in names.items() if len(people) > 1}

    if duplicates:
        print(f"\nPotential Duplicates: {len(duplicates)} names")
        for name, people in list(duplicates.items())[:5]:
            print(f"  '{name}': {len(people)} occurrences")
    else:
        print(f"\n[OK] No duplicate names detected")

    print("\n" + "=" * 80)
    print("[OK] Parsing test completed successfully!")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
