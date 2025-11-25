from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import export, families, files, ocr, parse, people, project, validation, gedcom_import, admin
from .core.settings import get_settings
from .db import init_db


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.project_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api_prefix = settings.api_prefix
    app.include_router(files.router, prefix=api_prefix)
    app.include_router(ocr.router, prefix=api_prefix)
    app.include_router(parse.router, prefix=api_prefix)
    app.include_router(people.router, prefix=api_prefix)
    app.include_router(families.router, prefix=api_prefix)
    app.include_router(export.router, prefix=api_prefix)
    app.include_router(project.router, prefix=api_prefix)
    app.include_router(validation.router, prefix=api_prefix)
    app.include_router(gedcom_import.router, prefix=api_prefix)
    app.include_router(admin.router, prefix=api_prefix)

    @app.on_event("startup")
    def _startup() -> None:
        init_db()

    return app


app = create_app()
