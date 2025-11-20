#!/usr/bin/env python3
"""
Fix 3+ digit generation markers by keeping only the last 1-2 digits.

Pattern: The LAST 1-2 digits of a generation marker are the real generation.
- If last 2 digits are 10, 11, or 12: keep them
- Otherwise: keep only the last digit

Examples:
  516-- → 6--
  956-- → 6--
  878-- → 8--
  688-- → 8--
  312-- → 12--
  612-- → 12--
"""
import sqlite3
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = r"C:\genealogy\data\app.db"

def fix_generation_markers(text):
    """
    Fix generation markers with extra leading digits.

    Two patterns to fix:
    1. ID concatenated with generation marker: -14027-- → -140 7--
    2. Word/name concatenated with gen marker: SPRAGUE4516-- → SPRAGUE 6--

    The last 1-2 digits before -- are the real generation:
    - If last 2 digits are 10, 11, or 12: keep them
    - Otherwise: keep only the last digit
    """
    original = text
    fixes = 0

    # Pattern 1: ID followed by 3+ digits and --
    # Example: -14027-- → -140 7--
    # Match: -DIGITS{3,}--
    def replace_id_gen(match):
        nonlocal fixes
        dash = match.group(1)  # The dash (-)
        all_digits = match.group(2)  # All the digits (e.g., "14027")

        # The last 1-2 digits are the generation
        if len(all_digits) >= 2:
            last_two = all_digits[-2:]
            last_one = all_digits[-1]

            if last_two in ['10', '11', '12']:
                id_part = all_digits[:-2]
                gen_part = last_two
            else:
                id_part = all_digits[:-1]
                gen_part = last_one
        else:
            # Shouldn't happen with {3,} but handle it
            id_part = all_digits
            gen_part = ""

        fixes += 1
        logger.info(f"  Fixed ID+gen: -{all_digits}-- → -{id_part} {gen_part}--")
        return f"{dash}{id_part} {gen_part}--"

    # Match: -(DIGITS{3,})-- where we capture dash, digits, and -- separately
    text = re.sub(r'(-)(\d{3,})(--)', lambda m: replace_id_gen(m) if len(m.group(2)) >= 3 else m.group(0), text)

    # Pattern 2: Word/name followed by 3+ digits and --
    # Example: SPRAGUE4516-- → SPRAGUE 6--
    # Match: LETTER+DIGITS{3,}--
    def replace_name_gen(match):
        nonlocal fixes
        name = match.group(1)  # Word (e.g., "SPRAGUE")
        all_digits = match.group(2)  # All digits (e.g., "4516")

        # The last 1-2 digits are the generation
        if len(all_digits) >= 2:
            last_two = all_digits[-2:]
            last_one = all_digits[-1]

            if last_two in ['10', '11', '12']:
                id_part = all_digits[:-2]
                gen_part = last_two
            else:
                id_part = all_digits[:-1]
                gen_part = last_one
        else:
            id_part = all_digits
            gen_part = ""

        fixes += 1
        if id_part:
            logger.info(f"  Fixed name+ID+gen: {name}{all_digits}-- → {name}-{id_part} {gen_part}--")
            return f"{name}-{id_part} {gen_part}--"
        else:
            logger.info(f"  Fixed name+gen: {name}{all_digits}-- → {name} {gen_part}--")
            return f"{name} {gen_part}--"

    text = re.sub(r'([A-Z]+)(\d{3,})(--)', lambda m: replace_name_gen(m), text)

    # Pattern 3: Standalone 3+ digit generation markers at line start or after space
    # Example: "   516-- " or " 878-- "
    def replace_standalone_gen(match):
        nonlocal fixes
        prefix = match.group(1)  # Whitespace before
        all_digits = match.group(2)  # All digits
        suffix = match.group(3)  # -- and after

        # The last 1-2 digits are the generation
        if len(all_digits) >= 2:
            last_two = all_digits[-2:]
            last_one = all_digits[-1]

            if last_two in ['10', '11', '12']:
                gen_part = last_two
            else:
                gen_part = last_one
        else:
            gen_part = all_digits

        fixes += 1
        logger.info(f"  Fixed standalone gen: {all_digits}-- → {gen_part}--")
        return f"{prefix}{gen_part}{suffix}"

    # Match: (whitespace or line start) + DIGITS{3,} + --
    text = re.sub(r'(\s|^)(\d{3,})(--\s)', lambda m: replace_standalone_gen(m), text)

    if fixes > 0:
        logger.info(f"  Total fixes in this page: {fixes}")

    return text


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        logger.info("Fixing generation markers with 3+ digits...")

        # Get all pagetext records
        cursor.execute("SELECT id, page_index, text FROM pagetext ORDER BY page_index")
        records = cursor.fetchall()

        fixes_applied = 0

        for record_id, page_index, text in records:
            fixed_text = fix_generation_markers(text)

            if fixed_text != text:
                cursor.execute("UPDATE pagetext SET text = ? WHERE id = ?", (fixed_text, record_id))
                fixes_applied += 1
                logger.info(f"Page {page_index}: Applied generation marker fixes")

        conn.commit()
        logger.info(f"Applied fixes to {fixes_applied} pages")

    except Exception as e:
        conn.rollback()
        logger.error(f"Error: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
