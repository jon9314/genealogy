# How Unique IDs Are Handled

## Summary

**The unique IDs ARE being captured!** They're stored in the `notes` field of each Person record.

## Parser Logic

Located in `parser.py` lines 264-268:

```python
id_matches = re.findall(r"-(\d+)", name_part)
name_part = re.sub(r"-\d+(?=\b)", "", name_part)
name_part = re.sub(r"\s+", " ", name_part).strip(' ,;')
if id_matches:
    notes_parts.extend([f"ID {match}" for match in id_matches])
```

### What Happens

**Input**: `7-- Catherine Ann SPRAGUE-1405 (1821)`

**Processing**:
1. Extract ID(s): `1405`
2. Remove from name: `Catherine Ann SPRAGUE`
3. Store in notes: `"ID 1405"`

### Database Schema

The `person` table includes:
- `name`: "Catherine Ann SPRAGUE" (clean display name)
- `given`: "Catherine Ann"
- `surname`: "SPRAGUE"
- `notes`: "ID 1405" ← **Unique ID stored here**
- `birth`: "1821"
- ... other fields

### Multiple IDs

If a person has multiple IDs (rare but possible):

**Input**: `8-- John SMITH-123-456 (1800)`

**Result**:
- `name`: "John SMITH"
- `notes`: "ID 123; ID 456"

## Why This Design?

1. **Clean display**: User sees "Catherine Ann SPRAGUE" not "Catherine Ann SPRAGUE-1405"
2. **Preserved data**: The unique ID is NOT lost - it's in the `notes` field
3. **Searchable**: You can query by ID using the notes field
4. **GEDCOM compatible**: The ID can be exported in GEDCOM notes/references

## Querying by Unique ID

```sql
-- Find person with unique ID 1405
SELECT * FROM person WHERE notes LIKE '%ID 1405%';

-- Find all persons with IDs
SELECT id, name, notes FROM person WHERE notes LIKE '%ID %';
```

## API Access

When you fetch a person via the API, the response includes:

```json
{
  "id": 218,
  "name": "Catherine Ann SPRAGUE",
  "given": "Catherine Ann",
  "surname": "SPRAGUE",
  "birth": "1821",
  "notes": "ID 1405",
  "gen": 7,
  ...
}
```

## OCR Concatenation Issue

The OCR error we discovered concatenates these IDs with generation markers:

**Wrong OCR**: `sp-Caroline MUNSON-14027-- Diedma SPRAGUE`

This becomes:
- ID: `14027` (should be `1402`)
- Generation: missing (should be `7`)

**After fix**: `sp-Caroline MUNSON-1402 7-- Diedma SPRAGUE`

This correctly becomes:
- Caroline MUNSON: ID `1402`, spouse of Obediah Hitchcock SPRAGUE
- Diedma SPRAGUE: Generation `7`, child of that family

## Bottom Line

**The unique IDs are fully utilized and preserved!**

They're just stored separately from the display name for cleaner presentation and better GEDCOM compatibility.
