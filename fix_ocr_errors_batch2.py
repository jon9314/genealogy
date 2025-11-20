#!/usr/bin/env python3
"""
Apply additional OCR error corrections based on problematic_lines.csv analysis.
"""
import sqlite3
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = r"C:\genealogy\data\app.db"

def apply_corrections(cursor):
    """Apply OCR corrections to pagetext table."""
    fixes_applied = 0

    # Get all pagetext records
    cursor.execute("SELECT id, page_index, text FROM pagetext ORDER BY page_index")
    records = cursor.fetchall()

    for record_id, page_index, text in records:
        original_text = text

        # Category 1: Extra leading digits in generation markers (3-digit patterns)
        # Pattern: \d{3}-- where last 1-2 digits are the real generation
        # Examples: 936--, 946--, 977--, 987--, 997--, 198--, 612--, etc.

        # First handle the ones where the correct gen is the last 2 digits (10-12)
        text = re.sub(r'\b\d(1[012])--', r'\1--', text)  # X10--, X11--, X12-- → 10--, 11--, 12--

        # Then handle where the correct gen is the last 1 digit (1-9)
        text = re.sub(r'\b\d{2}([1-9])--', r'\1--', text)  # XX1-- through XX9-- → 1-- through 9--

        # Category 2: Leading zero patterns (0XX--)
        text = re.sub(r'\b0([1-9]{1,2})--', r'\1--', text)  # 017--, 027--, etc. → 7--, 27--, etc.

        # Category 3: Generation marker character errors
        # L-- after closing paren (should be 11--)
        text = re.sub(r'\)L--', r')11--', text)

        # T-~ pattern (should be 7--)
        text = re.sub(r'T-~', r'7--', text)

        # Category 4: Tilde characters (should be dash)
        text = re.sub(r'~', r'-', text)

        # Category 5: Name OCR errors
        replacements = [
            ('BRADFORO', 'BRADFORD'),
            ('Rache]', 'Rachel'),
            ('Hichael', 'Michael'),
            ('NOORE', 'MOORE'),
            ('BLOON', 'BLOOM'),
            ('Hariam', 'Miriam'),
            ('Thonas', 'Thomas'),
            ('NEWCOHB', 'NEWCOMB'),
            ('BL1$S', 'BLISS'),
            ('Siby]', 'Sibyl'),
            ('LYNN%6', 'LYNN'),
            ('Hatthew', 'Matthew'),
            ('Canmie', 'Cammie'),
            ('Hary VAN', 'Mary VAN'),  # Hary → Mary (but only before VAN to avoid false positives)
            ('£.', 'E.'),
        ]

        for old, new in replacements:
            text = text.replace(old, new)

        # Category 6: Percentage signs in IDs
        text = re.sub(r'-(\d+)%(\d+)', r'-\1\2', text)  # -139%6 → -1396, etc.

        # Category 7: Comma instead of period in middle initials
        text = re.sub(r'([A-Z])\s*,\s+([A-Z])', r'\1. \2', text)  # "Peter J, BOCKMEYER" → "Peter J. BOCKMEYER"

        if text != original_text:
            cursor.execute("UPDATE pagetext SET text = ? WHERE id = ?", (text, record_id))
            fixes_applied += 1
            logger.info(f"Page {page_index}: Fixed line (Record ID {record_id})")

    return fixes_applied

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        logger.info("Applying OCR corrections (Batch 2)...")
        fixes = apply_corrections(cursor)
        conn.commit()
        logger.info(f"Applied {fixes} OCR corrections")

        # Show examples of changes
        logger.info("\nExamples of patterns fixed:")
        logger.info("- Extra leading digits: 936-- → 6--, 977-- → 7--, 612-- → 12--")
        logger.info("- Leading zeros: 017-- → 7--, 027-- → 7--")
        logger.info("- Character errors: L-- → 11--, T-~ → 7--")
        logger.info("- Tildes: ~ → - (in all names/IDs)")
        logger.info("- Name errors: BRADFORO→BRADFORD, Hichael→Michael, NOORE→MOORE, etc.")
        logger.info("- Percentage signs: -139%6 → -1396")
        logger.info("- Comma/period: J, → J.")

    except Exception as e:
        conn.rollback()
        logger.error(f"Error: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
