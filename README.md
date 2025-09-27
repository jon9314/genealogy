# Genealogy Workbench

A fully local-first genealogy workstation for importing scanned descendancy PDFs, running OCR with OCRmyPDF, parsing charts into linked family trees, editing via a grid and drag-and-drop graph, resolving duplicates, and exporting GEDCOM 5.5.1 and CSV files.

## Quick Start (Docker)

### Requirements
- Git 2.30 or newer
- Docker Engine 24+ with the Docker Compose plugin (on Ubuntu: `sudo apt install docker.io docker-compose-plugin`)
- At least 5 GB of free disk space for containers, OCR cache, and uploads

### Steps
1. Open a terminal on the Linux server (or workstation) that will host the app.
2. Clone the repository and change into it:
   ```bash
   git clone https://github.com/jon9314/genealogy.git
   cd genealogy
   ```
3. Create the data directory that will hold OCR output, uploads, and the SQLite database:
   ```bash
   mkdir -p data
   ```
4. Build and start the containers in the background:
   ```bash
   docker compose up -d --build
   ```
5. Wait until both services report "healthy" in `docker compose ps` (usually within a minute the first time).
6. From any machine on the same LAN, open `http://<server-ip>:8080` in your browser. Replace `<server-ip>` with the address or hostname of the Docker host. The FastAPI backend is also reachable at `http://<server-ip>:8000/api` if you need direct API access.

### Everyday Docker commands
- Check container status: `docker compose ps`
- Tail logs (Ctrl+C to stop streaming): `docker compose logs -f`
- Stop the stack: `docker compose down`
- Update to the latest version:
  ```bash
  git pull
  docker compose up -d --build
  ```

Uploads through the web UI can be as large as 1 GB, so make sure the `data` directory resides on storage with enough free space.

## Local Development (without Docker)

You can also run the backend and frontend directly on your workstation. These instructions assume macOS, Linux, or WSL.

### Requirements
- Python 3.11+
- Node.js 18+
- OCRmyPDF + Tesseract available on your PATH
  - macOS: `brew install ocrmypdf`
  - Ubuntu/Debian: `sudo apt install ocrmypdf tesseract-ocr`
  - Windows: install the [OCRmyPDF binaries](https://ocrmypdf.readthedocs.io/en/latest/installation.html#windows) and add them to PATH

### Backend setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .[dev]
uvicorn app.main:app --reload
```
The API lives at `http://localhost:8000/api` and stores its SQLite database at `../data/app.db`.

### Frontend setup
```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```
Visit `http://localhost:5173` to use the UI.

### Combined dev workflow
From the project root you can start both dev servers with one command:
```bash
make dev
```
`make dev` uses `npx concurrently` to run `uvicorn` and `npm run dev` side by side; press `Ctrl+C` to stop both.

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

## Running tests

Backend tests focus on the parser heuristics and GEDCOM output:
```bash
cd backend
pytest
```

## Sample data

`./samples/descendancy-sample.pdf` is a two-page synthetic descendancy chart you can upload immediately to exercise OCR, parsing, and graph editing.

## Key environment variables

- `GENEALOGY_DATABASE_PATH` - override the SQLite path (defaults to `./data/app.db`)
- `GENEALOGY_OCRMYPDF_EXECUTABLE` - provide an alternate OCRmyPDF binary
- `GENEALOGY_OCRMYPDF_LANGUAGE` - change the Tesseract language pack (default `eng`)
- `GENEALOGY_OCRMYPDF_REMOVE_BACKGROUND` - set to `true` to enable the `--remove-background` flag
- `GENEALOGY_OCRMYPDF_FAST_WEB_VIEW_MB` - set the `--fast-web-view` target size (default `200`, set to `0` to disable)

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

Everything runs offline once the dependencies are installed.
