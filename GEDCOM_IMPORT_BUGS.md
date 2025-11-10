# GEDCOM Import - Remaining Issues

**Status:** Partially Fixed - Core bugs resolved, API usage needs rewrite
**Date:** November 9, 2025

---

## ✅ Fixed Issues (Completed)

1. **Missing Import** - `OperationalError` not imported in parser.py
   - Fixed: Added `from sqlalchemy.exc import OperationalError`

2. **Field Name Mismatches** - Source model field references
   - Fixed: `filename` → `name`
   - Fixed: `filepath` → `path`
   - Fixed: `parse_done` → `stage == "parsed"`

3. **Wrong xref Attribute** - Using `record.xref` instead of `record.xref_id`
   - Fixed: All references to `.xref` changed to `.xref_id`

4. **Wrong File Type** - Using StringIO instead of BytesIO
   - Fixed: `from io import BytesIO` and `BytesIO(gedcom_data.encode('utf-8'))`

5. **Missing Dependency** - `gedcom-validator` doesn't exist on PyPI
   - Fixed: Removed from pyproject.toml

---

## ❌ Remaining Issues (Need Fix)

### Issue #6: Incorrect ged4py API Usage

**Location:** `backend/app/core/gedcom.py` lines 195-217

**Problem:** Code uses `record.sub_record()` method which doesn't exist in ged4py library.

**Current Code:**
```python
name_record = record.sub_record("NAME")  # ❌ sub_record() doesn't exist!
name = name_record.value if name_record else "Unknown"

birth_record = record.sub_record("BIRT")  # ❌ Wrong method
birth_date = birth_record.sub_record("DATE").value  # ❌ Wrong method
```

**Correct API:**
```python
# Individual records have direct attributes
name = record.name  # ✅ Individual.name is a Name object

# For sub-tags, use sub_tag() or sub_tag_value()
birth_record = record.sub_tag("BIRT")  # ✅ Returns Record or None
if birth_record:
    birth_date = birth_record.sub_tag_value("DATE")  # ✅ Returns value directly
```

**ged4py API Reference:**
- `Individual` objects (from `records0("INDI")`) have special attributes:
  - `.name` - Returns Name object with tuple value `(given, surname, suffix)`
  - `.sex` - Returns "M", "F", or None
  - `.father` - Returns Individual reference
  - `.mother` - Returns Individual reference

- `Record` objects use:
  - `.sub_tag(tag)` - Returns first Record with tag, or None
  - `.sub_tags(tag)` - Returns list of all Records with tag
  - `.sub_tag_value(tag)` - Returns value of first matching tag
  - `.value` - The value of this record

- `FAM` records:
  - `.sub_tag("HUSB")` returns the **Individual** object (not xref string!)
  - `.sub_tag("WIFE")` returns the **Individual** object
  - To get xref: `record.sub_tag("HUSB").xref_id` if the tag exists

### Issue #7: Name Parsing Logic

**Problem:** Current code assumes `name_record.value` is a string with "/" separators.

**Reality:** Individual.name returns a Name object with tuple value:
```python
record.name  # Returns Name('John Doe')
record.name.value  # Returns ('John', 'Doe', '')  # (given, surname, suffix)
```

**Required Fix:**
```python
if hasattr(record, 'name') and record.name:
    name_parts = record.name.value if hasattr(record.name, 'value') else (None, None, None)
    given = name_parts[0] if name_parts[0] else None
    surname = name_parts[1] if len(name_parts) > 1 and name_parts[1] else None
```

### Issue #8: HUSB/WIFE xref Extraction

**Location:** `backend/app/core/gedcom.py` lines 280-281

**Problem:**
```python
husband_xref = record.sub_record("HUSB").value if record.sub_record("HUSB") else None
```

**Issue:** `sub_tag("HUSB")` returns an **Individual object**, not a Record with a value!

**Correct Approach:**
```python
husb_tag = record.sub_tag("HUSB")
husband_xref = husb_tag.xref_id if husb_tag else None
```

Or if HUSB points to an individual xref:
```python
# FAM records store xrefs in sub-tags differently
husb_records = list(record.sub_tags("HUSB"))
if husb_records:
    # The value IS the xref string like "@I1@"
    husband_xref = husb_records[0].value
```

---

## 🔧 Recommended Fix Strategy

### Option 1: Rewrite import_gedcom() Function (2-3 hours)

Completely rewrite the function to use correct ged4py API:

```python
def import_gedcom(session: Session, gedcom_data: str) -> dict:
    from io import BytesIO
    from ged4py import GedcomReader
    from .models import Source

    gedcom_bytes = gedcom_data.encode('utf-8')
    reader = GedcomReader(BytesIO(gedcom_bytes))

    # Create import source
    import_source = Source(
        name="GEDCOM Import",
        path=f"import_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.ged",
        ocr_done=True,
        stage="parsed"
    )
    session.add(import_source)
    session.flush()

    xref_to_person_id = {}
    imported_persons = []
    errors = []

    # Import individuals using correct API
    for indi in reader.records0("INDI"):
        try:
            xref = indi.xref_id

            # Use Individual attributes directly
            name_parts = indi.name.value if indi.name else (None, None, None)
            given = name_parts[0] if name_parts[0] else None
            surname = name_parts[1] if len(name_parts) > 1 else None
            full_name = f"{given or ''} {surname or ''}".strip() or "Unknown"

            sex = indi.sex if hasattr(indi, 'sex') else None

            # Get birth date
            birth_date = None
            birth_tag = indi.sub_tag("BIRT")
            if birth_tag:
                birth_date = birth_tag.sub_tag_value("DATE")

            # Get death date
            death_date = None
            death_tag = indi.sub_tag("DEAT")
            if death_tag:
                death_date = death_tag.sub_tag_value("DATE")

            # Create person
            person = Person(
                name=full_name,
                given=given,
                surname=surname,
                birth=birth_date,
                death=death_date,
                sex=sex,
                gen=0,
                source_id=import_source.id
            )
            session.add(person)
            session.flush()

            xref_to_person_id[xref] = person.id
            imported_persons.append({"id": person.id, "name": full_name})

        except Exception as e:
            errors.append(f"Error importing {indi.xref_id}: {str(e)}")

    # Import families
    imported_families = []
    for fam in reader.records0("FAM"):
        try:
            xref = fam.xref_id

            # Get parent xrefs from sub-tag values
            husband_xref = None
            wife_xref = None

            husb_tag = fam.sub_tag("HUSB")
            if husb_tag and hasattr(husb_tag, 'value'):
                husband_xref = husb_tag.value

            wife_tag = fam.sub_tag("WIFE")
            if wife_tag and hasattr(wife_tag, 'value'):
                wife_xref = wife_tag.value

            husband_id = xref_to_person_id.get(husband_xref)
            wife_id = xref_to_person_id.get(wife_xref)

            if not husband_id and not wife_id:
                errors.append(f"Family {xref}: No valid parents")
                continue

            family = Family(
                husband_id=husband_id,
                wife_id=wife_id,
                source_id=import_source.id,
                is_single_parent=not (husband_id and wife_id)
            )
            session.add(family)
            session.flush()
            imported_families.append({"id": family.id})

            # Link children
            for chil_tag in fam.sub_tags("CHIL"):
                child_xref = chil_tag.value if hasattr(chil_tag, 'value') else None
                child_id = xref_to_person_id.get(child_xref)
                if child_id:
                    child_link = Child(
                        family_id=family.id,
                        person_id=child_id,
                        order_index=0
                    )
                    session.add(child_link)

        except Exception as e:
            errors.append(f"Error importing family {fam.xref_id}: {str(e)}")

    session.commit()

    return {
        "persons": imported_persons,
        "families": imported_families,
        "children": [],
        "source_id": import_source.id,
        "errors": errors
    }
```

### Option 2: Use Alternative Library (1-2 hours)

Consider using `python-gedcom` library instead of `ged4py`:
- Simpler API
- Better documentation
- Active maintenance

### Option 3: Defer GEDCOM Import (0 hours now)

- Core workflow (Upload → OCR → Parse → Edit → Export) works
- GEDCOM import is a "nice to have" feature
- Fix later when user requests it

---

## Priority Assessment

**Low Priority** - GEDCOM import is not critical for main workflow:
1. Users primarily work with scanned PDFs (OCR path works)
2. Export to GEDCOM works fine
3. Import is for merging external data (edge case)

**Recommend:** Fix after completing:
- Frontend test infrastructure ✅ (in progress)
- AI duplicate resolution
- Accessibility improvements
- Performance optimization (virtualization)

---

## Test Coverage

**Current Status:**
- ❌ 5 GEDCOM import tests failing (API mismatch)
- ✅ 13 other backend tests passing
- Total: 13/18 passing (72%)

**After Fix:**
- Expected: 18/18 passing (100%)

---

## Next Steps

1. **Document this issue** ✅ (this file)
2. **Set up frontend testing** (in progress)
3. **Return to GEDCOM import** when:
   - User specifically requests it
   - All higher-priority items complete
   - Time available: 2-3 hours for full rewrite

---

## References

- ged4py documentation: https://github.com/ivannav/ged4py
- ged4py model.py source: Key to understanding Individual vs Record
- Current implementation: `backend/app/core/gedcom.py` lines 146-375
