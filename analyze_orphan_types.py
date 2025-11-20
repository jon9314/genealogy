#!/usr/bin/env python3
"""
Analyze orphans to distinguish between:
1. True orphans (principal persons with no parent link)
2. Spouses (correctly linked to families, just not as children)
"""
import sqlite3

DB_PATH = r"C:\genealogy\data\app.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all persons not in child table (gen > 1)
    cursor.execute("""
        SELECT p.id, p.page_index, p.gen, p.name, p.birth
        FROM person p
        LEFT JOIN child c ON c.person_id = p.id
        WHERE c.person_id IS NULL AND p.gen > 1
        ORDER BY p.gen, p.page_index
    """)

    orphans = cursor.fetchall()
    print(f"Total 'orphans' (persons not in child table): {len(orphans)}")
    print()

    # Check which are actually spouses in families
    true_orphans = []
    linked_spouses = []

    for person_id, page_index, gen, name, birth in orphans:
        # Check if this person is a husband or wife in any family
        cursor.execute("""
            SELECT COUNT(*) FROM family
            WHERE husband_id = ? OR wife_id = ?
        """, (person_id, person_id))

        is_spouse = cursor.fetchone()[0] > 0

        if is_spouse:
            linked_spouses.append((person_id, page_index, gen, name, birth))
        else:
            true_orphans.append((person_id, page_index, gen, name, birth))

    print(f"Linked spouses (not orphans): {len(linked_spouses)}")
    print(f"TRUE orphans (not linked anywhere): {len(true_orphans)}")
    print()

    # Break down true orphans by generation
    print("TRUE ORPHANS BY GENERATION:")
    gen_counts = {}
    for person_id, page_index, gen, name, birth in true_orphans:
        gen_counts[gen] = gen_counts.get(gen, 0) + 1

    for gen in sorted(gen_counts.keys()):
        print(f"  Gen {gen}: {gen_counts[gen]} true orphans")

    print()

    # Break down true orphans by page
    print("TRUE ORPHANS BY PAGE:")
    page_counts = {}
    for person_id, page_index, gen, name, birth in true_orphans:
        page_counts[page_index] = page_counts.get(page_index, 0) + 1

    for page in sorted(page_counts.keys()):
        print(f"  Page {page}: {page_counts[page]} true orphans")

    print()

    # Show some examples of true orphans
    print("SAMPLE TRUE ORPHANS (first 20):")
    print("ID | Gen | Name | Birth | Page")
    print("-" * 70)
    for person_id, page_index, gen, name, birth in true_orphans[:20]:
        print(f"{person_id:3} | {gen:3} | {name:30} | {birth or '':4} | {page_index}")

    print()

    # Analyze generation gaps in gen_tracker
    print("GENERATION TRACKING ANALYSIS:")
    print("Checking for generations that might be missing from gen_tracker...")

    # Get all principal persons (not spouses) ordered by page and appearance
    cursor.execute("""
        SELECT p.id, p.gen, p.page_index, p.name
        FROM person p
        ORDER BY p.page_index, p.id
    """)

    all_persons = cursor.fetchall()

    # Simulate gen_tracker to find gaps
    gen_tracker_simulation = {}
    missing_parents = []

    for person_id, gen, page_index, name in all_persons:
        # Check if this person should have a parent
        if gen > 1:
            expected_parent_gen = gen - 1
            if expected_parent_gen not in gen_tracker_simulation:
                # Check if they're actually linked as a child
                cursor.execute("""
                    SELECT family_id FROM child WHERE person_id = ?
                """, (person_id,))

                if cursor.fetchone() is None:
                    # Not linked and no parent in tracker
                    missing_parents.append((person_id, gen, page_index, name, expected_parent_gen))

        # Update gen_tracker simulation
        gen_tracker_simulation[gen] = person_id

    print(f"Found {len(missing_parents)} persons with missing parent generation in tracker")

    if missing_parents:
        print("\nSample of persons with missing parent generations (first 10):")
        print("ID | Gen | Missing Parent Gen | Name | Page")
        print("-" * 80)
        for person_id, gen, page_index, name, expected_gen in missing_parents[:10]:
            print(f"{person_id:3} | {gen:3} | {expected_gen:18} | {name:30} | {page_index}")

    conn.close()

if __name__ == "__main__":
    main()
