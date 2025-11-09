# Project Overview

This is a full-stack genealogy workbench application. It allows users to upload scanned descendancy PDFs, performs OCR on them, parses the text to build family trees, and provides tools for editing and exporting the data.

The backend is a Python application built with the **FastAPI** framework. It uses **SQLModel** and **SQLAlchemy** for database interaction with a SQLite database. **Alembic** is used for database migrations. OCR functionality is provided by **OCRmyPDF** and **Tesseract**.

The frontend is a modern **React** application built with **Vite**. It uses **React Router** for navigation, **React Flow** for displaying and interacting with the family tree graph, and **TanStack Table** for grid-based data editing.

The application is designed to be run locally, either directly on the host machine or using **Docker**.

# Building and Running

## Docker (Recommended)

The easiest way to run the application is with Docker.

- **Build and start:** `docker compose up -d --build`
- **Check status:** `docker compose ps`
- **View logs:** `docker compose logs -f`
- **Stop:** `docker compose down`

The application will be available at `http://<server-ip>:8080`.

## Local Development

You can also run the backend and frontend services directly on your machine.

- **Run both services concurrently:** `make dev`

### Backend

- **Install dependencies:** `pip install -e .[dev]` (from the `backend` directory)
- **Run server:** `uvicorn app.main:app --reload` (from the `backend` directory)
- **Run tests:** `make test` or `pytest` (from the `backend` directory)
- **Run database migrations:** `make migrate`

### Frontend

- **Install dependencies:** `npm install` (from the `frontend` directory)
- **Run dev server:** `npm run dev` (from the `frontend` directory)
- **Run tests:** `npm test` (from the `frontend` directory)

# Development Conventions

- The backend code is located in the `backend/app` directory.
- FastAPI endpoints are defined in the `backend/app/api` directory.
- Core business logic (parsing, OCR, etc.) is in the `backend/app/core` directory.
- The frontend code is in the `frontend/src` directory.
- React components are in `frontend/src/components`.
- Page-level routes are in `frontend/src/routes`.
- The project uses `pytest` for backend testing and `vitest` for frontend testing.
