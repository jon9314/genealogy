#!/usr/bin/env python3
"""
Comprehensive OCR fix script - applies ALL corrections in proper sequence.

This script fixes OCR errors that prevent proper genealogical linking:
1. Basic OCR character errors (Batch 1)
2. Name/surname errors (Batch 2)
3. Generation marker concatenation issues (Batch 3)

Run this AFTER OCR but BEFORE parsing.
"""
import sqlite3
import re
import logging
import hashlib

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

DB_PATH = r"C:\genealogy\data\app.db"


def apply_all_fixes(cursor):
    """Apply all OCR corrections to pagetext table."""

    cursor.execute("SELECT id, page_index, text FROM pagetext ORDER BY page_index")
    records = cursor.fetchall()

    total_fixes = 0

    for record_id, page_index, text in records:
        original_text = text
        page_fixes = 0

        # ===== BATCH 1: Basic OCR character errors =====

        # Generation marker spacing: allow zero spaces after --
        # (Already handled by parser pattern, but ensure clean spacing)
        text = re.sub(r'(\d{1,2})--([A-Z])', r'\1-- \2', text)

        # Letter/digit confusion in generation markers
        text = re.sub(r'\bl1--', '11--', text)  # lowercase L → 11
        text = re.sub(r'\\l--', '11--', text)    # backslash-l → 11
        text = re.sub(r'\\t--', '11--', text)    # backslash-t → 11
        text = re.sub(r'\\(\d)--', r'1\1--', text)  # backslash-digit → 1-digit
        text = re.sub(r'\{(\d)--', r'1\1--', text)  # curly brace-digit → 1-digit

        # Dash variants in generation markers
        text = re.sub(r'(\d)-~', r'\1--', text)   # N-~ → N--
        text = re.sub(r'(\d)\*-', r'\1--', text)  # N*- → N--
        text = re.sub(r'(\d)- ', r'\1-- ', text)  # N- → N-- (with space)

        # Remove middle initials (they cause false PERSON_PATTERN_ALT matches)
        text = re.sub(r'\b([A-Z])\.\s+(?=[A-Z]{2,})', '', text)  # X. NAME → NAME

        # ===== BATCH 2: Name and surname OCR errors =====

        name_replacements = [
            ('BRADFORO', 'BRADFORD'),
            ('Rache]', 'Rachel'),
            ('Siby]', 'Sibyl'),
            ('Hichael', 'Michael'),
            ('NOORE', 'MOORE'),
            ('BLOON', 'BLOOM'),
            ('Hariam', 'Miriam'),
            ('Thonas', 'Thomas'),
            ('NEWCOHB', 'NEWCOMB'),
            ('BL1$S', 'BLISS'),
            ('LYNN%', 'LYNN'),  # Handles LYNN%6 → LYNN6
            ('Hatthew', 'Matthew'),
            ('Canmie', 'Cammie'),
        ]

        for old, new in name_replacements:
            text = text.replace(old, new)

        # Context-sensitive name fixes
        text = re.sub(r'Hary VAN', 'Mary VAN', text)  # Only before VAN

        # Punctuation fixes
        text = re.sub(r'([A-Z])\s*,\s+([A-Z])', r'\1. \2', text)  # J, B → J. B
        text = re.sub(r'£\.', 'E.', text)  # £. → E.

        # Tilde replacement (in names and IDs)
        text = re.sub(r'~', '-', text)

        # Percentage signs in IDs (e.g., -139%6 → -1396)
        text = re.sub(r'-(\d+)%(\d+)', r'-\1\2', text)

        # ===== BATCH 3: Generation marker concatenation fixes =====

        # Pattern 1: ID concatenated with generation marker
        # Example: sp-Caroline MUNSON-14027-- → sp-Caroline MUNSON-1402 7--
        def fix_id_concat(match):
            nonlocal page_fixes
            dash = match.group(1)
            all_digits = match.group(2)
            double_dash = match.group(3)

            # Only fix if we have 4+ digits (ID + gen combined)
            if len(all_digits) < 4:
                return match.group(0)

            # Last 1-2 digits are the generation
            last_two = all_digits[-2:]
            if last_two in ['10', '11', '12']:
                id_part = all_digits[:-2]
                gen_part = last_two
            else:
                id_part = all_digits[:-1]
                gen_part = all_digits[-1]

            page_fixes += 1
            return f"{dash}{id_part} {gen_part}{double_dash}"

        text = re.sub(r'(-)(\d{4,})(--)', fix_id_concat, text)

        # Pattern 2: Name concatenated with ID and generation marker
        # Example: SPRAGUE4516-- → SPRAGUE-451 6--
        def fix_name_concat(match):
            nonlocal page_fixes
            name = match.group(1)
            all_digits = match.group(2)
            double_dash = match.group(3)

            # Only fix if we have 3+ digits (ID + gen combined)
            if len(all_digits) < 3:
                return match.group(0)

            # Last 1-2 digits are the generation
            last_two = all_digits[-2:]
            if last_two in ['10', '11', '12']:
                id_part = all_digits[:-2]
                gen_part = last_two
            else:
                id_part = all_digits[:-1]
                gen_part = all_digits[-1]

            page_fixes += 1

            if id_part:
                return f"{name}-{id_part} {gen_part}{double_dash}"
            else:
                return f"{name} {gen_part}{double_dash}"

        text = re.sub(r'([A-Z]{2,})(\d{3,})(--)', fix_name_concat, text)

        # Pattern 3: Standalone 3+ digit generation markers
        # Example: 936-- → 6--, 612-- → 12--
        def fix_standalone_gen(match):
            nonlocal page_fixes
            prefix = match.group(1)
            all_digits = match.group(2)
            double_dash = match.group(3)

            # Only fix if we have 3+ digits
            if len(all_digits) < 3:
                return match.group(0)

            # Last 1-2 digits are the generation
            last_two = all_digits[-2:]
            if last_two in ['10', '11', '12']:
                gen_part = last_two
            else:
                gen_part = all_digits[-1]

            page_fixes += 1
            return f"{prefix}{gen_part}{double_dash}"

        # Match at word boundaries or after whitespace
        text = re.sub(r'(\s)(\d{3,})(--)', fix_standalone_gen, text)

        # ===== Save if changed =====

        if text != original_text:
            cursor.execute("UPDATE pagetext SET text = ? WHERE id = ?", (text, record_id))
            total_fixes += 1
            if page_fixes > 0:
                logger.info(f"Page {page_index}: Applied {page_fixes} fixes")

    return total_fixes


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        logger.info("="*80)
        logger.info("APPLYING ALL OCR CORRECTIONS")
        logger.info("="*80)
        logger.info("")

        pages_fixed = apply_all_fixes(cursor)
        conn.commit()

        logger.info("")
        logger.info(f"Applied corrections to {pages_fixed} pages")
        logger.info("")
        logger.info("OCR corrections complete!")
        logger.info("Next step: Trigger parser with POST /api/parse/1")

    except Exception as e:
        conn.rollback()
        logger.error(f"Error: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
