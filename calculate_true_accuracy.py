#!/usr/bin/env python3
"""
Calculate TRUE accuracy excluding spouses from orphan count.
"""
import sqlite3

DB_PATH = r"C:\genealogy\data\app.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Total persons
    cursor.execute("SELECT COUNT(*) FROM person")
    total_persons = cursor.fetchone()[0]

    # Persons linked as children
    cursor.execute("SELECT COUNT(DISTINCT person_id) FROM child")
    linked_as_children = cursor.fetchone()[0]

    # Persons who are spouses (husband or wife in family table)
    cursor.execute("""
        SELECT COUNT(DISTINCT p.id)
        FROM person p
        INNER JOIN family f ON f.husband_id = p.id OR f.wife_id = p.id
    """)
    linked_as_spouses = cursor.fetchone()[0]

    # Gen 1 persons (progenitors, don't need parents)
    cursor.execute("SELECT COUNT(*) FROM person WHERE gen = 1")
    gen1_count = cursor.fetchone()[0]

    # TRUE orphans: not in child table, not in family table, gen > 1
    cursor.execute("""
        SELECT COUNT(*)
        FROM person p
        LEFT JOIN child c ON c.person_id = p.id
        LEFT JOIN family f ON f.husband_id = p.id OR f.wife_id = p.id
        WHERE c.person_id IS NULL
          AND f.id IS NULL
          AND p.gen > 1
    """)
    true_orphans = cursor.fetchone()[0]

    # Calculate persons who ARE linked (either as children or as spouses)
    properly_linked = linked_as_children + linked_as_spouses

    # Expected linkable: total - gen1 (since gen1 doesn't need parents)
    expected_linkable = total_persons - gen1_count

    print("=" * 80)
    print("TRUE ACCURACY CALCULATION")
    print("=" * 80)
    print()
    print(f"Total persons in database: {total_persons}")
    print(f"  Gen 1 (progenitors, no parents needed): {gen1_count}")
    print(f"  Gen 2+ (should be linked): {expected_linkable}")
    print()
    print(f"Persons successfully linked:")
    print(f"  As children (linked to parent family): {linked_as_children}")
    print(f"  As spouses (linked to own family): {linked_as_spouses}")
    print(f"  TOTAL properly linked: {properly_linked}")
    print()
    print(f"TRUE orphans (Gen 2+, not linked anywhere): {true_orphans}")
    print()

    # Calculate accuracy
    true_accuracy = (properly_linked / expected_linkable * 100) if expected_linkable > 0 else 0

    print("=" * 80)
    print(f"TRUE ACCURACY: {properly_linked}/{expected_linkable} = {true_accuracy:.1f}%")
    print("=" * 80)
    print()

    # Show the 7 true orphans in detail
    print("DETAILS OF 7 TRUE ORPHANS:")
    print("-" * 80)

    cursor.execute("""
        SELECT p.id, p.gen, p.page_index, p.name, p.birth
        FROM person p
        LEFT JOIN child c ON c.person_id = p.id
        LEFT JOIN family f ON f.husband_id = p.id OR f.wife_id = p.id
        WHERE c.person_id IS NULL
          AND f.id IS NULL
          AND p.gen > 1
        ORDER BY p.page_index, p.id
    """)

    orphans = cursor.fetchall()

    for person_id, gen, page_index, name, birth in orphans:
        print(f"Person {person_id:3} | Gen {gen:2} | Page {page_index} | {name:40} | Birth: {birth or 'N/A'}")

        # Get OCR context
        cursor.execute("SELECT text FROM pagetext WHERE page_index = ?", (page_index,))
        page_text_result = cursor.fetchone()

        if page_text_result:
            page_text = page_text_result[0]
            lines = page_text.split('\n')

            # Find the line
            for i, line in enumerate(lines):
                if name in line or (birth and str(birth) in line):
                    print(f"  OCR: {line.strip()}")
                    if i > 0:
                        print(f"  Prev: {lines[i-1].strip()}")
                    if i < len(lines) - 1:
                        print(f"  Next: {lines[i+1].strip()}")
                    break
        print()

    conn.close()

if __name__ == "__main__":
    main()
