#!/usr/bin/env python3
"""
Generate updated problematic_lines.csv after batch 2 OCR fixes.
"""
import sqlite3
import csv

DB_PATH = r"C:\genealogy\data\app.db"
OUTPUT_CSV = r"C:\genealogy\problematic_lines_v2.csv"

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all orphaned persons (gen > 1, not linked to any family as child)
    cursor.execute("""
        SELECT p.id, p.page_index, p.gen, p.name, p.birth
        FROM person p
        LEFT JOIN child c ON c.person_id = p.id
        WHERE c.person_id IS NULL AND p.gen > 1
        ORDER BY p.page_index, p.id
    """)

    orphans = cursor.fetchall()
    print(f"Found {len(orphans)} orphaned persons")

    # For each orphan, get the OCR context
    rows = []

    for person_id, page_index, gen, name, birth in orphans:
        # Get the full OCR text for this page
        cursor.execute("""
            SELECT text FROM pagetext
            WHERE page_index = ?
        """, (page_index,))

        result = cursor.fetchone()
        if not result:
            continue

        page_text = result[0]
        lines = page_text.split('\n')

        # Find the line containing this person
        # We'll search for the person's name in the OCR
        person_line = None
        line_index = None
        prev_line = ""
        next_line = ""

        for i, line in enumerate(lines):
            if name in line or (birth and str(birth) in line):
                person_line = line
                line_index = i
                prev_line = lines[i-1] if i > 0 else ""
                next_line = lines[i+1] if i < len(lines)-1 else ""
                break

        if person_line is None:
            person_line = f"[Not found in OCR]"
            line_index = -1

        # Categorize the problem
        problem_type = "Orphan"
        notes = ""

        if gen >= 10:
            notes = "High generation - check if gen marker correct"

        if page_index in [0, 1, 3, 4]:
            if notes:
                notes += "; On problem page"
            else:
                notes = "On problem page"

        # Check if this is a spouse (no surname extraction)
        if not name or ' ' not in name.strip():
            problem_type = "No surname"
            notes = "Spouse with no surname extracted"

        rows.append({
            "Person ID": person_id,
            "Page": page_index,
            "Line Index": line_index,
            "Gen": gen,
            "Name Extracted": name,
            "Birth": birth or "",
            "Full OCR Line": person_line.strip(),
            "Previous Line": prev_line.strip(),
            "Next Line": next_line.strip(),
            "Problem Type": problem_type,
            "Notes": notes
        })

    # Write to CSV
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ["Person ID", "Page", "Line Index", "Gen", "Name Extracted", "Birth",
                      "Full OCR Line", "Previous Line", "Next Line", "Problem Type", "Notes"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} problematic lines to {OUTPUT_CSV}")

    # Generate summary by category
    summary_csv = r"C:\genealogy\ocr_issues_summary_v2.csv"

    summary_rows = []
    summary_rows.append({"Category": "Total Orphans", "Count": len(orphans)})

    # Count by page
    page_counts = {}
    for row in rows:
        page = row["Page"]
        page_counts[page] = page_counts.get(page, 0) + 1

    for page in sorted(page_counts.keys()):
        summary_rows.append({"Category": f"Page {page}", "Count": page_counts[page]})

    # Count high generations
    high_gen_count = len([r for r in rows if r["Gen"] >= 10])
    summary_rows.append({"Category": "High Generation (10+)", "Count": high_gen_count})

    # Count spouses
    spouse_count = len([r for r in rows if r["Problem Type"] == "No surname"])
    summary_rows.append({"Category": "Spouses (no surname)", "Count": spouse_count})

    with open(summary_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["Category", "Count"])
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"Wrote summary to {summary_csv}")

    conn.close()

if __name__ == "__main__":
    main()
