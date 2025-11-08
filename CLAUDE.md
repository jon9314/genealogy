# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a local-first genealogy workstation for importing scanned descendancy PDFs, running OCR with OCRmyPDF, parsing charts into linked family trees, editing via a grid and drag-and-drop graph, resolving duplicates, and exporting GEDCOM 5.5.1 and CSV files.

**Technology Stack:**
- Backend: Python 3.11+ with FastAPI, SQLModel, SQLAlchemy
- Frontend: React 18 with TypeScript, Vite, React Flow, TanStack Table
- Database: SQLite
- OCR: OCRmyPDF + Tesseract
- Containerization: Docker Compose

**Task Tracking:**
- See `TODO.md` for pending fixes, improvements, and feature requests that need to be addressed

## Common Commands

### Development (Local)

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .[dev]
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev  # Starts Vite dev server on port 5173
```

**Run both simultaneously:**
```bash
make dev  # Uses concurrently to run both dev servers
```

### Testing

**Backend tests (pytest):**
```bash
cd backend
pytest                    # Run all tests locally (requires pip install -e .[dev])
pytest tests/test_parser.py  # Run specific test file
pytest -v                # Verbose output
pytest -k "test_name"    # Run tests matching pattern

# Or run tests in Docker (no local setup needed)
make test-docker         # Runs tests in Docker container with all dependencies
```

**Frontend tests (vitest):**
```bash
cd frontend
npm test
```

### Linting

```bash
cd frontend
npm run lint
```

### Docker

**Production:**
```bash
make build              # Build containers
make up                 # Start services
make down               # Stop services
docker compose up -d --build  # Build and start in background
docker compose ps       # Check container status
docker compose logs -f  # Tail logs
```

**Development (with hot reload and test dependencies):**
```bash
make dev-build          # Build dev containers with pytest, etc.
make dev-up             # Start dev services with source mounted
make dev-down           # Stop dev services
make test-docker        # Run pytest in Docker container
```

## Architecture

### Backend Structure

The backend is a FastAPI application organized into modular API routers and core business logic:

**Entry point:** `backend/app/main.py`
- Creates the FastAPI app with CORS middleware
- Registers API routers (files, ocr, parse, people, families, export, project)
- Initializes the database on startup

**Core modules in `backend/app/core/`:**
- `parser.py` - OCR text parsing into Person/Family/Child entities. Key function: `parse_ocr_text()`
  - Uses generation-aware parsing with a stack to track parent-child relationships
  - Normalizes OCR text with `normalize_ocr_text()` which handles hyphenation, dash variants, and header removal
  - Patterns: `PERSON_PATTERN` matches "Gen-- Name (birth-death)" format, `SPOUSE_PATTERN` matches "sp- Name" format
  - Builds genealogical relationships by maintaining a generation stack and linking children to parent families
  - Handles approximate dates/data by detecting keywords like "abt", "circa", "?" and sets `approx` flags
- `models.py` - SQLModel entities (Source, Person, Family, Child) with upsert logic
  - Person deduplication uses Levenshtein distance (≤2) on normalized names + birth year matching
  - Family uniqueness enforced by `source_id + husband_id + wife_id` constraint
  - `line_key` field tracks the original OCR line to enable idempotent re-parsing
- `gedcom.py` - GEDCOM 5.5.1 export with ged4py fallback to manual writer
- `ocr_runner.py` - Subprocess wrapper for OCRmyPDF with configurable options
  - Uses `--skip-text` flag to preserve existing text in PDFs (only OCRs image-only pages)
- `settings.py` - Environment-based configuration using pydantic-settings

**Database:** `backend/app/db.py` manages SQLite connection and initialization

**API routers in `backend/app/api/`:**
- `files.py` - Upload, list, delete PDF sources
- `ocr.py` - Trigger OCR on a source, check OCR status
- `parse.py` - Parse OCR text into genealogy entities
- `people.py` - CRUD operations for persons
- `families.py` - Family management and reparenting logic
- `export.py` - GEDCOM and CSV export endpoints
- `project.py` - Save/load entire database snapshots as JSON

### Frontend Structure

React SPA with React Router and Zustand for state management:

**Entry point:** `frontend/src/main.tsx`
- Renders `App.tsx` which sets up React Router with routes

**Routes in `frontend/src/routes/`:**
- `Upload.tsx` - PDF file upload interface
- `OCR.tsx` - Trigger OCR processing for uploaded files
- `Parse.tsx` - Parse OCR text into genealogy entities
- `Table.tsx` - Editable grid view of persons using TanStack Table
- `Graph.tsx` - Interactive family tree visualization with React Flow
- `Review.tsx` - Duplicate person review dashboard grouped by surname/given/birth year
- `Export.tsx` - GEDCOM and CSV download interface
- `Home.tsx` - Landing page

**Components in `frontend/src/components/`:**
- `GraphView.tsx` - React Flow canvas with drag-to-reparent functionality
- `PersonForm.tsx` - Person edit form
- `FamilyCard.tsx` - Family display card
- `FileCard.tsx` - Source file card
- `Sidebar.tsx` - Navigation sidebar
- `Toolbar.tsx` - Action toolbar

**Hooks:** `frontend/src/hooks/useUndoRedo.tsx` provides undo/redo functionality

**API client:** `frontend/src/lib/api.ts` - Axios-based API wrapper with typed functions

### Data Flow

1. **Upload** → PDF files stored in `./data/uploads`, Source records created in DB
2. **OCR** → OCRmyPDF processes PDF, per-page text stored in PageText table
3. **Parse** → Parser reads PageText, creates Person/Family/Child entities with generation-aware logic
4. **Edit** → Users modify entities via Table or Graph views, changes persisted to SQLite
5. **Export** → GEDCOM or CSV generated from DB entities

### Key Parsing Logic

The parser in `backend/app/core/parser.py` is the heart of the system:

- **Generation stack:** Tracks current parent context as parser encounters descendants
- **Line normalization:** Handles OCR artifacts (hyphenation, dash variants, headers)
- **Pattern matching:** Recognizes "Gen-- Name (birth-death)" and "sp- Name" formats
- **Idempotent re-parsing:** Uses `line_key` (SHA1 of source_id:page:line:text) to upsert, not duplicate
- **Approximate data handling:** Detects "abt", "circa", "?", trailing "-" and sets `approx` boolean flags
- **Spouse handling:** When a spouse is encountered, parser either upgrades single-parent family or creates new family

## Environment Variables

Prefix all with `GENEALOGY_`:

- `GENEALOGY_DATABASE_PATH` - SQLite path (default: `./data/app.db`)
- `GENEALOGY_OCRMYPDF_EXECUTABLE` - OCRmyPDF binary path (default: `ocrmypdf`)
- `GENEALOGY_OCRMYPDF_LANGUAGE` - Tesseract language pack (default: `eng`)
- `GENEALOGY_OCRMYPDF_REMOVE_BACKGROUND` - Enable background removal (default: `false`)
- `GENEALOGY_OCRMYPDF_FAST_WEB_VIEW_MB` - Target size for fast web view optimization (default: `200`, set to `0` to disable)
- `GENEALOGY_OCRMYPDF_TIMEOUT_SECS` - OCR timeout in seconds (default: `600`)

## Database Migrations

This project uses **Alembic** for database schema migrations:

- Migrations are in `backend/alembic/versions/`
- Migrations run automatically on backend startup (in `db.py:init_db()`)
- To create a new migration after model changes:
  ```bash
  cd backend
  alembic revision --autogenerate -m "description of changes"
  alembic upgrade head  # Apply the migration
  ```
- Migration history: `alembic history`
- Rollback: `alembic downgrade -1`

## Development Notes

- All file operations (uploads, OCR output) are stored under `./data/` which is volume-mounted in Docker
- The frontend proxies `/api` requests to the backend via Vite dev server configuration
- Project save/load creates JSON snapshots of the entire database for backup/restore
- GEDCOM export uses the ged4py library if available, falls back to manual GEDCOM 5.5.1 writer
- Parser handles multiple records on one OCR line by splitting on `\d+--` and `sp-` patterns
- OCRmyPDF uses `--skip-text` to preserve existing text, only OCRing image-only pages
