# OCR Issues Report

## Files Created:
1. **problematic_lines.csv** - Detailed list of all 113 orphaned persons with OCR context
2. **ocr_issues_summary.csv** - Summary of issue types and priorities

## How to Use:

### Step 1: Open problematic_lines.csv
- Contains all persons that couldn't be linked to parents
- Columns:
  - Person ID, Page, Line Index
  - Generation, Name Extracted, Birth Year
  - **Full OCR Line** - What the parser saw
  - **Previous/Next Line** - Context
  - Problem Type, Notes

### Step 2: Compare with PDF
- Open your PDF to the page number indicated
- Find the person by name or birth year
- Compare what OCR extracted vs what PDF shows
- Note any differences (missing chars, wrong chars, etc.)

### Step 3: Priority Issues
Check ocr_issues_summary.csv for categories:
- **HIGH priority**: Spouses not linking, Problem pages (1, 3, 4)
- **MEDIUM priority**: Principal persons, High generation numbers

## Current Accuracy:
- Andrew NEWCOMB Lt.: 100% (15/15 children linked) ✓
- Overall: 61.9% (187/302 persons linked)
- Pages 2, 6: >90% accuracy
- Pages 1, 3, 4: <50% accuracy (need most work)

## OCR Errors Already Fixed: 143
- Generation markers (l1--, N-~, N*-, etc.)
- Middle initials (X. patterns)
- Spacing issues

## Next Steps:
1. Focus on high-priority issues first
2. Check pages 1, 3, 4 systematically
3. Look for patterns in OCR errors (repeated mistakes)
