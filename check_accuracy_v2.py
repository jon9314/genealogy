#!/usr/bin/env python3
"""
Check parser accuracy after batch 2 OCR corrections.
"""
import sqlite3

DB_PATH = r"C:\genealogy\data\app.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Total persons and children linked
    cursor.execute("SELECT COUNT(*) FROM person")
    total_persons = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT person_id) FROM child")
    linked_persons = cursor.fetchone()[0]

    orphans = total_persons - linked_persons
    orphan_pct = (orphans / total_persons * 100) if total_persons > 0 else 0

    print(f"OVERALL ACCURACY:")
    print(f"Total persons: {total_persons}")
    print(f"Linked to families: {linked_persons} ({linked_persons/total_persons*100:.1f}%)")
    print(f"Orphans (Gen > 1): {orphans} ({orphan_pct:.1f}%)")
    print()

    # Andrew NEWCOMB Lt. accuracy
    cursor.execute("""
        SELECT p.id, p.name, p.gen
        FROM person p
        WHERE p.surname = 'NEWCOMB' AND LOWER(p.name) LIKE '%andrew%lt%'
        ORDER BY p.id
    """)
    andrews = cursor.fetchall()

    if andrews:
        andrew_id = andrews[0][0]
        andrew_name = andrews[0][1]
        print(f"ANDREW NEWCOMB Lt. (Person {andrew_id}):")

        # Get families where Andrew is husband
        cursor.execute("""
            SELECT f.id, w.name as wife_name, COUNT(c.person_id) as num_children
            FROM family f
            LEFT JOIN person w ON f.wife_id = w.id
            LEFT JOIN child c ON c.family_id = f.id
            WHERE f.husband_id = ?
            GROUP BY f.id
            ORDER BY f.id
        """, (andrew_id,))

        families = cursor.fetchall()
        total_children = 0

        for fam_id, wife_name, num_children in families:
            print(f"  Family {fam_id} (sp: {wife_name}): {num_children} children")
            total_children += num_children

        print(f"  TOTAL: {total_children} children")
        print()

        # Expected: 7 from first wife Sarah, 8 from second wife Anna = 15 total
        expected = 15
        if total_children == expected:
            print(f"  [OK] 100% accuracy ({total_children}/{expected})")
        else:
            print(f"  [!!] {total_children/expected*100:.1f}% accuracy ({total_children}/{expected})")
    else:
        print("Andrew NEWCOMB Lt. not found!")

    print()

    # Page-by-page breakdown
    print("PAGE-BY-PAGE BREAKDOWN:")
    cursor.execute("""
        SELECT p.page_index, COUNT(*) as total,
               COUNT(c.person_id) as linked,
               COUNT(*) - COUNT(c.person_id) as orphans
        FROM person p
        LEFT JOIN child c ON c.person_id = p.id
        WHERE p.gen > 1
        GROUP BY p.page_index
        ORDER BY p.page_index
    """)

    page_stats = cursor.fetchall()
    for page_idx, total, linked, orphans in page_stats:
        linked_pct = (linked / total * 100) if total > 0 else 0
        orphan_pct = (orphans / total * 100) if total > 0 else 0
        print(f"  Page {page_idx}: {linked}/{total} linked ({linked_pct:.1f}%), {orphans} orphans ({orphan_pct:.1f}%)")

    print()

    # Count orphans by generation
    print("ORPHANS BY GENERATION:")
    cursor.execute("""
        SELECT p.gen, COUNT(*) as num_orphans
        FROM person p
        LEFT JOIN child c ON c.person_id = p.id
        WHERE c.person_id IS NULL AND p.gen > 1
        GROUP BY p.gen
        ORDER BY p.gen
    """)

    gen_stats = cursor.fetchall()
    for gen, num in gen_stats:
        print(f"  Gen {gen}: {num} orphans")

    conn.close()

if __name__ == "__main__":
    main()
