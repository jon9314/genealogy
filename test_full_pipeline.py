#!/usr/bin/env python3
"""Test full OCR and parsing pipeline with OpenRouter LLM integration."""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Load .env file
from dotenv import load_dotenv
load_dotenv()

from app.db import init_db, get_session
from app.core.models import Source, PageText, Person, Family
from app.core.ocr_runner import queue_ocr_job, get_ocr_job_status, get_ocr_result
from app.core.parser import parse_ocr_text
from app.core.settings import get_settings
from sqlmodel import select
import time


def main():
    """Run the full pipeline test."""
    print("=" * 80)
    print("Testing Full OCR & Parsing Pipeline with OpenRouter LLM")
    print("=" * 80)

    # Initialize database
    init_db()

    # Get settings
    settings = get_settings()
    print(f"\nLLM Provider: {settings.llm_provider}")
    if settings.llm_provider == "openrouter":
        print(f"OCR Model: {settings.openrouter_ocr_model}")
        print(f"Parse Model: {settings.openrouter_parse_model}")
        print(f"Context Parse Enabled: {settings.openrouter_use_context_parse}")

    # Find a PDF to process
    pdf_path = Path("data/uploads/75f18b9361ff4032a97750436f45c6aa-andrew_newcomb_descendace.pdf").absolute()

    if not pdf_path.exists():
        print(f"\n[ERROR] PDF not found: {pdf_path}")
        return 1

    print(f"\nProcessing PDF: {pdf_path.name}")
    print(f"File size: {pdf_path.stat().st_size / 1024:.1f} KB")

    # Create source record
    session = next(get_session())

    # Check if source already exists
    existing = session.exec(
        select(Source).where(Source.name == pdf_path.name)
    ).first()

    if existing:
        print(f"\nUsing existing source (ID: {existing.id})")
        source = existing
        # Clear old data
        for page in session.exec(select(PageText).where(PageText.source_id == source.id)).all():
            session.delete(page)
        for person in session.exec(select(Person).where(Person.source_id == source.id)).all():
            session.delete(person)
        session.commit()
    else:
        source = Source(
            name=pdf_path.name,
            path=str(pdf_path.absolute()),
            stage="uploaded"
        )
        session.add(source)
        session.commit()
        session.refresh(source)
        print(f"\nCreated new source (ID: {source.id})")

    # Step 1: Run OCR
    print("\n" + "-" * 80)
    print("Step 1: Running OCR (this may take a minute...)")
    print("-" * 80)

    try:
        ocr_output = Path(f"data/ocr/{pdf_path.stem}-ocr.pdf")
        ocr_output.parent.mkdir(parents=True, exist_ok=True)

        # Queue OCR job
        job_id = queue_ocr_job(pdf_path, ocr_output)
        print(f"OCR job queued: {job_id}")

        # Poll for completion
        print("Waiting for OCR to complete", end="", flush=True)
        while True:
            status = get_ocr_job_status(job_id)

            if status["status"] == "completed":
                print(" [DONE]")
                break
            elif status["status"] == "failed":
                print(f"\n[ERROR] OCR failed: {status.get('error', 'Unknown error')}")
                return 1

            print(".", end="", flush=True)
            time.sleep(2)

        # Get OCR results
        texts = get_ocr_result(job_id)
        print(f"[OK] OCR completed successfully - {len(texts)} pages")

        # Save to database
        existing_pages = session.exec(
            select(PageText).where(PageText.source_id == source.id)
        ).all()
        for page in existing_pages:
            session.delete(page)

        for index, text in enumerate(texts):
            page = PageText(source_id=source.id, page_index=index, text=text)
            session.add(page)

        source.pages = len(texts)
        source.ocr_done = True
        source.stage = "ocr_done"
        session.add(source)
        session.commit()

    except Exception as e:
        print(f"\n[ERROR] OCR failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Check OCR results
    session.refresh(source)
    page_texts = session.exec(
        select(PageText).where(PageText.source_id == source.id)
    ).all()

    print(f"\nOCR Results:")
    print(f"  Pages processed: {len(page_texts)}")

    if page_texts:
        total_chars = sum(len(pt.text) for pt in page_texts)
        print(f"  Total text extracted: {total_chars} characters")

        # Show sample from first page
        if page_texts[0].text:
            sample = page_texts[0].text[:200].replace('\n', ' ')
            print(f"  Sample (page 1): {sample}...")

    # Step 2: Parse with LLM
    print("\n" + "-" * 80)
    print("Step 2: Parsing OCR text with OpenRouter LLM")
    print("-" * 80)

    try:
        stats = parse_ocr_text(source.id)

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
    print("Step 3: Reviewing Parsed Data")
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
        gen = person.generation or 0
        if gen not in by_generation:
            by_generation[gen] = []
        by_generation[gen].append(person)

    print(f"\nPersons by Generation:")
    for gen in sorted(by_generation.keys()):
        people = by_generation[gen]
        print(f"  Generation {gen}: {len(people)} persons")

    # Show sample persons
    print(f"\nSample Persons (first 10):")
    print("-" * 80)
    for i, person in enumerate(persons[:10], 1):
        birth = f"{person.birth_year}" if person.birth_year else "?"
        death = f"{person.death_year}" if person.death_year else "?"
        approx = " (approx)" if person.birth_approx or person.death_approx else ""
        print(f"{i:2}. Gen {person.generation or '?'}: {person.name} ({birth}-{death}){approx}")

    # Data quality checks
    print("\n" + "-" * 80)
    print("Data Quality Analysis")
    print("-" * 80)

    persons_with_dates = sum(1 for p in persons if p.birth_year or p.death_year)
    persons_with_both = sum(1 for p in persons if p.birth_year and p.death_year)
    persons_approx = sum(1 for p in persons if p.birth_approx or p.death_approx)

    print(f"\nDate Coverage:")
    print(f"  Persons with any date: {persons_with_dates}/{len(persons)} ({persons_with_dates/len(persons)*100:.1f}%)")
    print(f"  Persons with both dates: {persons_with_both}/{len(persons)} ({persons_with_both/len(persons)*100:.1f}%)")
    print(f"  Approximate dates flagged: {persons_approx}/{len(persons)} ({persons_approx/len(persons)*100:.1f}%)")

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
        print(f"\nNo duplicate names detected")

    print("\n" + "=" * 80)
    print("[OK] Pipeline test completed successfully!")
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
