#!/usr/bin/env python3
"""
Reload source from uploads folder and trigger full processing pipeline.
"""
import sqlite3
from pathlib import Path

DB_PATH = r"C:\genealogy\data\app.db"
UPLOADS_DIR = Path(r"C:\genealogy\data\uploads")

def main():
    # Find the andrew_newcomb PDF
    pdf_files = list(UPLOADS_DIR.glob("*andrew_newcomb*.pdf"))

    if not pdf_files:
        print("Error: No andrew_newcomb PDF found in uploads!")
        return

    pdf_path = pdf_files[0]
    print(f"Found PDF: {pdf_path.name}")

    # Get number of pages (we know it's 7 from before)
    pages = 7

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Insert source record
        cursor.execute("""
            INSERT INTO source (name, path, pages, ocr_done, stage, parser_version)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (pdf_path.name, str(pdf_path), pages, False, 'uploaded', None))

        source_id = cursor.lastrowid
        conn.commit()

        print(f"Created source record with ID: {source_id}")
        print(f"Name: {pdf_path.name}")
        print(f"Path: {pdf_path}")
        print(f"Pages: {pages}")
        print()
        print("Next steps:")
        print(f"1. Trigger OCR: curl -X POST http://localhost:8001/api/ocr/{source_id}")
        print(f"2. Wait for OCR to complete")
        print(f"3. Apply OCR fixes")
        print(f"4. Parse: curl -X POST http://localhost:8001/api/parse/{source_id}")

    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
