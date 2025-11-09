# TODO - Fixes and Improvements

This file tracks potential fixes, improvements, and feature requests for the genealogy workstation.

## High Priority (Quick Wins & Biggest Impact)

### Quick Wins - Easy to Implement
- [x] Show unparsed lines to user instead of silently logging (parser.py:289) - COMPLETED 2025-11-08
- [x] Add parse summary before committing ("Found 47 people, 12 families, 3 unparsed lines") - COMPLETED 2025-11-08
- [x] Expose source page/line in person detail view (already tracked in `page_index`/`line_index`) - COMPLETED 2025-11-08
- [x] Add progress bar/indicator for OCR processing - COMPLETED 2025-11-08
- [x] Implement project auto-save (every N minutes, keep last 5 versions) - COMPLETED 2025-11-08

### Biggest Impact - Accuracy & Error Prevention
- [x] OCR text review step before parsing - COMPLETED 2025-11-08
  - ✅ Allow users to view/edit raw OCR text before parsing
  - ✅ Highlight lines that don't match expected patterns
  - ✅ Show Tesseract confidence scores (COMPLETED 2025-11-08 - optional feature)
- [x] Improved duplicate detection - COMPLETED 2025-11-08
  - ✅ Add soundex/metaphone matching for phonetically similar names (William vs Bill)
  - ✅ Add birth year tolerance (±2 years) for OCR errors
- [x] Data validation warnings - COMPLETED 2025-11-08
  - ✅ Check for impossible dates (child born before parent, death before birth)
  - ✅ Flag suspiciously large age gaps between spouses or generations
  - ✅ Warn about duplicate names within the same family

## Medium Priority

### Parser & OCR Enhancements
- [x] Parser pattern flexibility - COMPLETED 2025-11-08
  - ✅ Support alternative generation formats (`1. Name` or `I. Name`)
  - ✅ Handle edge cases like `(b. 1850)` vs `(1850-)` vs `(1850-living)`
- [x] Better error handling - COMPLETED 2025-11-08
  - ✅ Collect and display unparseable lines to users (completed previously)
  - ✅ Provide explanatory error messages for OCR failures
  - ✅ Suggest fixes (missing Tesseract language pack, corrupted PDF, etc.)

### Workflow & UX Improvements
- [x] Visual stepper/progress indicator: Upload → OCR → Review → Parse → Edit → Export - COMPLETED 2025-11-08
- [x] Show processing stage for each source in file list - COMPLETED 2025-11-08
- [x] Parse preview/confirmation dialog before committing to database - COMPLETED 2025-11-08
- [x] Batch operations - COMPLETED 2025-11-08
  - ✅ Select multiple sources and OCR/delete all at once
  - ✅ Bulk edit features (e.g., set sex for all "John" to M)
  - ✅ Mass duplicate resolution (accept all suggestions)
- [x] Enhanced undo/redo - COMPLETED 2025-11-08
  - ✅ Document what actions are undoable
  - ✅ Show undo history
  - ✅ Add "Save checkpoint" feature for major milestones

### Source & Citation Features
- [x] Source citation tracking in UI - COMPLETED 2025-11-09
  - [x] Add "Jump to source" button from person record to original PDF page - COMPLETED 2025-11-09
  - [x] Display source page/line references in person details - COMPLETED 2025-11-09
- [ ] Relationship validation
  - [x] Visual family tree validator with suspicious relationships highlighted - COMPLETED 2025-11-09
  - [x] "Orphan" detection (people with no family connections) - COMPLETED 2025-11-09

### Export & Import Features
- [x] Export preview and validation - COMPLETED 2025-11-09
  - [x] Show GEDCOM preview before download - COMPLETED 2025-11-09
  - [x] Validate GEDCOM against spec and show warnings - COMPLETED 2025-11-09
  - [x] Warn about data loss (fields that won't export) - COMPLETED 2025-11-09
- [x] Import from GEDCOM - COMPLETED 2025-11-09 (initial by Gemini), FIXED 2025-11-09 (by Claude)
  - [x] Allow importing existing GEDCOM trees - COMPLETED 2025-11-09
  - [x] Merge OCR'd data with existing research - COMPLETED 2025-11-09
  - [x] Import rollback if user doesn't like the result - COMPLETED 2025-11-09
  - [x] Fix critical bugs (StringIO, xref mapping, children linking) - COMPLETED 2025-11-09
  - [x] Proper error handling and validation - COMPLETED 2025-11-09
  - [x] Source tracking for imported records - COMPLETED 2025-11-09

## Low Priority / Nice to Have

### Performance Optimizations
- [x] Real-time OCR progress (showing current page/total pages) - COMPLETED 2025-11-09
- [x] Streaming parser updates instead of waiting for completion - COMPLETED 2025-11-09
- [x] Background processing for OCR with notifications - COMPLETED 2025-11-09
- [x] Queue multiple OCR jobs - COMPLETED 2025-11-09
- [x] Incremental parsing (parse new pages only, not entire source) - COMPLETED 2025-11-09
- [ ] Store parser version in database to detect when re-parsing is needed

### UX Polish
- [ ] Keyboard shortcuts
  - Navigation (tab through records, arrow keys in table)
  - Quick actions (Ctrl+S to save, Ctrl+E to export)
- [ ] Global search across all people
- [ ] Advanced filters
  - Show only people with missing birth dates
  - Show only approximate data
  - Filter by generation, surname, date range
- [ ] Dark mode support
- [ ] Mobile responsiveness (at least for viewing)
- [ ] Quick Start wizard for first-time users

### Data Safety & Backup
- [ ] Automatic project backups
  - Auto-save every N minutes
  - Keep last 5-10 versions with timestamps
  - Easy restore from backup
- [ ] Export validation
  - Test GEDCOM files against validators before download
  - Report validation errors/warnings

## Completed

- [x] Add database migrations with Alembic (2025-11-08)
- [x] Fix OCR to handle PDFs with existing text using `--skip-text` flag (2025-11-08)
- [x] Add Docker dev environment with test dependencies (2025-11-08)
- [x] Create CLAUDE.md documentation (2025-11-08)
- [x] Show unparsed lines to user instead of silently logging (2025-11-08)
- [x] Add parse summary with user-friendly messages (2025-11-08)
- [x] Expose source page/line in person detail view (2025-11-08)
- [x] Add animated progress indicator for OCR processing (2025-11-08)
- [x] Implement project auto-save (every 5 minutes, keeps last 5 versions) (2025-11-08)
- [x] OCR text review and editing before parsing with pattern validation (2025-11-08)
- [x] Tesseract confidence scores with optional extraction and display (2025-11-08)
- [x] Improved duplicate detection with phonetic matching and birth year tolerance (2025-11-08)
- [x] Data validation warnings for impossible dates, age gaps, and duplicate names (2025-11-08)
- [x] Parser pattern flexibility supporting alternative generation formats (1. Name, I. Name) (2025-11-08)
- [x] Enhanced vital date parsing for edge cases (b. 1850, d. 1920, 1850-living) (2025-11-08)
- [x] Improved OCR error messages with helpful suggestions and troubleshooting (2025-11-08)
- [x] Visual workflow stepper component showing progress through stages (2025-11-08)
- [x] Processing stage tracking for each source (uploaded, ocr_done, reviewed, parsed, edited, ready_to_export) (2025-11-08)
- [x] Batch operations for OCR and delete with selection UI (2025-11-08)
- [x] Enhanced undo/redo with history viewer and checkpoint feature (2025-11-08)
- [x] Bulk edit features for setting fields on multiple people (2025-11-08)
- [x] Mass duplicate resolution with auto-resolve functionality (2025-11-08)
- [x] Parse preview dialog with confirmation before committing to database (2025-11-08)

## Notes

### Parser Behavior (Current)
- Collects and displays unparseable lines to users in Parse UI (parser.py:335)
- Supports multiple generation formats:
  - Standard: `II-- Name` (double dash format)
  - Numeric: `1. Name` (period format)
  - Roman: `I. Name` (Roman numeral with period)
- Handles multiple vital date formats:
  - Standard: `(1850-1920)` or `(1850-)`
  - Birth only: `(b. 1850)` or `(b 1850)`
  - Death only: `(d. 1920)` or `(d 1920)`
  - Still living: `(1850-living)` or `(1850-liv)`
- Uses Levenshtein distance ≤2 for name matching
- Uses metaphone phonetic matching for similar-sounding names (William/Bill, Stephen/Steven)
- Allows ±2 year tolerance for birth year matching (handles OCR errors)
- Detects "abt", "circa", "?", trailing "-" for approximate data
- Handles multiple records per line by splitting on generation markers and `sp-` patterns

### Technical Debt
- [x] Fix 2 failing tests in `test_models_upsert.py` (incorrect function signatures) - COMPLETED 2025-11-09
- [x] Fix deprecated Pydantic `env` parameter warnings in `settings.py` - COMPLETED 2025-11-09
- [x] Add proper type hints to frontend TypeScript code - COMPLETED 2025-11-09
  - ✅ Eliminated all explicit `any` types
  - ✅ Created proper interfaces for parse results (SamplePerson, SampleFamily, ParsePreview)
  - ✅ Type-safe error handling with axios.isAxiosError()
  - ✅ Proper event handler types

### Future Ideas
- Integration with FamilySearch/Ancestry APIs (if permitted)
- OCR language auto-detection
- AI-assisted duplicate resolution
- Collaborative editing features
- Timeline view of family events
- Map view for birthplaces/locations
