# TODO - Fixes and Improvements

This file tracks potential fixes, improvements, and feature requests for the genealogy workstation.

## High Priority (Quick Wins & Biggest Impact)

### Quick Wins - Easy to Implement
- [ ] Show unparsed lines to user instead of silently logging (parser.py:289)
- [ ] Add parse summary before committing ("Found 47 people, 12 families, 3 unparsed lines")
- [ ] Expose source page/line in person detail view (already tracked in `page_index`/`line_index`)
- [ ] Add progress bar/indicator for OCR processing
- [ ] Implement project auto-save (every N minutes, keep last 5 versions)

### Biggest Impact - Accuracy & Error Prevention
- [ ] OCR text review step before parsing
  - Allow users to view/edit raw OCR text before parsing
  - Highlight lines that don't match expected patterns
  - Show Tesseract confidence scores for low-quality text
- [ ] Improved duplicate detection
  - Add soundex/metaphone matching for phonetically similar names (William vs Bill)
  - Add birth year tolerance (±2 years) for OCR errors
- [ ] Data validation warnings
  - Check for impossible dates (child born before parent, death before birth)
  - Flag suspiciously large age gaps between spouses or generations
  - Warn about duplicate names within the same family

## Medium Priority

### Parser & OCR Enhancements
- [ ] Parser pattern flexibility
  - Support alternative generation formats (`1. Name` or `I. Name`)
  - Handle edge cases like `(b. 1850)` vs `(1850-)` vs `(1850-living)`
- [ ] Better error handling
  - Collect and display unparseable lines to users
  - Provide explanatory error messages for OCR failures
  - Suggest fixes (missing Tesseract language pack, corrupted PDF, etc.)

### Workflow & UX Improvements
- [ ] Visual stepper/progress indicator: Upload → OCR → Review → Parse → Edit → Export
- [ ] Show processing stage for each source in file list
- [ ] Parse preview/confirmation dialog before committing to database
- [ ] Batch operations
  - Select multiple sources and OCR/parse all at once
  - Bulk edit features (e.g., set sex for all "John" to M)
  - Mass duplicate resolution (accept all suggestions)
- [ ] Enhanced undo/redo
  - Document what actions are undoable
  - Show undo history
  - Add "Save checkpoint" feature for major milestones

### Source & Citation Features
- [ ] Source citation tracking in UI
  - Add "Jump to source" button from person record to original PDF page
  - Display source page/line references in person details
- [ ] Relationship validation
  - Visual family tree validator with suspicious relationships highlighted
  - "Orphan" detection (people with no family connections)

### Export & Import Features
- [ ] Export preview and validation
  - Show GEDCOM preview before download
  - Validate GEDCOM against spec and show warnings
  - Warn about data loss (fields that won't export)
- [ ] Import from GEDCOM
  - Allow importing existing GEDCOM trees
  - Merge OCR'd data with existing research
  - Import rollback if user doesn't like the result

## Low Priority / Nice to Have

### Performance Optimizations
- [ ] Real-time OCR progress (showing current page/total pages)
- [ ] Streaming parser updates instead of waiting for completion
- [ ] Background processing for OCR with notifications
- [ ] Queue multiple OCR jobs
- [ ] Incremental parsing (parse new pages only, not entire source)
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

## Notes

### Parser Behavior (Current)
- Silently skips unparseable lines (logs only) - see parser.py:289
- Uses Levenshtein distance ≤2 for name matching
- Detects "abt", "circa", "?", trailing "-" for approximate data
- Handles multiple records per line by splitting on `\d+--` and `sp-` patterns

### Technical Debt
- Fix 2 failing tests in `test_models_upsert.py` (incorrect function signatures)
- Fix deprecated Pydantic `env` parameter warnings in `settings.py`
- Consider adding type hints to frontend TypeScript code

### Future Ideas
- Integration with FamilySearch/Ancestry APIs (if permitted)
- OCR language auto-detection
- AI-assisted duplicate resolution
- Collaborative editing features
- Timeline view of family events
- Map view for birthplaces/locations
