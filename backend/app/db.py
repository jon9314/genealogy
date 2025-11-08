from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import sqlalchemy
from sqlmodel import Session, SQLModel, create_engine

from .core.settings import get_settings


settings = get_settings()
_engine = create_engine(
    settings.database_url,
    echo=settings.database_echo,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    """Create or update database schema."""
    # Import models to ensure SQLModel metadata is populated
    from .core import models  # noqa: F401

    # Check if database exists and has tables
    inspector = sqlalchemy.inspect(_engine)
    existing_tables = inspector.get_table_names()

    if not existing_tables:
        # Fresh install - create all tables
        SQLModel.metadata.create_all(_engine)
    else:
        # Existing database - run migrations to update schema
        _run_migrations()


def _run_migrations() -> None:
    """Run Alembic migrations to latest version."""
    try:
        from alembic import command
        from alembic.config import Config
        from pathlib import Path
        import logging

        logger = logging.getLogger(__name__)

        # Get the alembic.ini path
        backend_dir = Path(__file__).parent.parent
        alembic_ini = backend_dir / "alembic.ini"

        if not alembic_ini.exists():
            logger.warning(f"Alembic config not found at {alembic_ini}, skipping migrations")
            return

        alembic_cfg = Config(str(alembic_ini))

        # Run migrations to head
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")
    except Exception as exc:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Migration failed: {exc}")
        # Don't crash the app if migrations fail
        raise


@contextmanager
def session_scope() -> Iterator[Session]:
    session = Session(_engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Iterator[Session]:
    with session_scope() as session:
        yield session
