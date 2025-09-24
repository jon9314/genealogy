# Genealogy Workbench

A fully local-first genealogy workstation for importing scanned descendancy PDFs, running OCR with OCRmyPDF, parsing charts into linked family trees, editing via a grid and drag-and-drop graph, resolving duplicates, and exporting GEDCOM 5.5.1 and CSV files.

## Features

- Local PDF uploads stored under `./data/uploads`
- OCR pipeline powered by OCRmyPDF + Tesseract with deskew/rotate/optimize presets
- Generation-aware parser that builds `Person`, `Family`, and `Child` relations with spouse handling
- React + React Flow UI with TanStack Table grid editing, undo/redo, and drag-to-reparent graph
- Duplicate review dashboard grouped by surname/given/birth year heuristics
- GEDCOM 5.5.1 and CSV exports generated entirely locally (GedcomWriter fallback to manual writer)
- Project save/load snapshots plus automatic `./data/lastProject.json`

## Repository structure

```
genealogy/
  backend/           # FastAPI + SQLModel service
    app/
      api/           # REST endpoints
      core/          # settings, parser, gedcom, OCR wrapper
      main.py        # FastAPI app factory
    tests/           # Pytest suite (parser + GEDCOM)
    Dockerfile
    pyproject.toml
  frontend/          # React 18 + Vite UI
    src/
      routes/        # Page-level routes
      components/    # Shared components
      hooks/         # Undo/redo provider
      lib/           # API client + type defs
    Dockerfile
    package.json
  data/              # Persistent storage for uploads, OCR, and DB
  samples/           # Example descendancy chart PDF
  docker-compose.yml
  Makefile
  README.md          # You are here
```

## Prerequisites (local, no Docker)

- Python 3.11+
- Node.js 18+
- OCRmyPDF + Tesseract installed on your system
  - **macOS**: `brew install ocrmypdf`
  - **Ubuntu/Debian**: `sudo apt install ocrmypdf tesseract-ocr`
  - **Windows**: install [OCRmyPDF binaries](https://ocrmypdf.readthedocs.io/en/latest/installation.html#windows) and add to PATH

### Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # on Windows: .venv\Scripts\activate
pip install -e .[dev]
uvicorn app.main:app --reload
```

The API lives at `http://localhost:8000/api` and stores its SQLite database at `./data/app.db`.

### Frontend setup

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Visit `http://localhost:5173` to use the UI.

### Combined dev workflow

From the project root:

```bash
make dev
```

This uses `npx concurrently` to start `uvicorn` and `npm run dev` side-by-side (press `Ctrl+C` to stop both).

## Docker workflow

```bash
# build images
make build

# start services (backend on :8000, frontend on :5173)
make up

# stop containers
make down
```

The backend container mounts `./data` to persist database, OCR PDFs, and project archives.

## Running tests

Backend tests focus on the parser heuristics and GEDCOM output:

```bash
cd backend
pytest
```

## Sample data

`./samples/descendancy-sample.pdf` is a two-page synthetic descendancy chart you can upload immediately to exercise OCR, parsing, and graph editing.

## Key environment variables

- `GENEALOGY_DATABASE_PATH` – override the SQLite path (defaults to `./data/app.db`)
- `GENEALOGY_OCRMYPDF_EXECUTABLE` – provide an alternate OCRmyPDF binary
- `GENEALOGY_OCRMYPDF_LANGUAGE` – change the Tesseract language pack (default `eng`)
- `GENEALOGY_OCRMYPDF_REMOVE_BACKGROUND` – set to `true` to enable background removal flag

## API overview

| Endpoint | Description |
| --- | --- |
| `POST /api/files/upload` | Upload one or more PDFs |
| `POST /api/ocr/{source_id}` | Run OCR and persist per-page text |
| `POST /api/parse/{source_id}` | Parse OCR text into people/families |
| `GET /api/persons` | List people with filters |
| `PATCH /api/persons/{id}` | Update person fields |
| `DELETE /api/persons/{id}` | Remove a person |
| `GET /api/families` | List families + children |
| `POST /api/families/reparent` | Reassign a child to a new parent/family |
| `POST /api/export/gedcom` | Download GEDCOM |
| `POST /api/export/csv` | Download CSV |
| `POST /api/project/save` | Persist DB snapshot to JSON |
| `POST /api/project/open` | Restore from project JSON |

Everything runs offline—no external services are required once dependencies are installed.
