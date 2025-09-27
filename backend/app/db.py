from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

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
    SQLModel.metadata.create_all(_engine)
    _apply_migrations()


def _apply_migrations() -> None:
    with _engine.connect() as conn:
        def has_column(table: str, column: str) -> bool:
            result = conn.exec_driver_sql(f"PRAGMA table_info('{table}')")
            return any(row[1] == column for row in result.fetchall())

        if not has_column("person", "line_key"):
            conn.exec_driver_sql("ALTER TABLE person ADD COLUMN line_key TEXT")
        if not has_column("person", "normalized_given"):
            conn.exec_driver_sql("ALTER TABLE person ADD COLUMN normalized_given TEXT")
        if not has_column("person", "normalized_surname"):
            conn.exec_driver_sql("ALTER TABLE person ADD COLUMN normalized_surname TEXT")
        if not has_column("person", "birth_year"):
            conn.exec_driver_sql("ALTER TABLE person ADD COLUMN birth_year INTEGER")

        if not has_column("family", "source_id"):
            conn.exec_driver_sql("ALTER TABLE family ADD COLUMN source_id INTEGER")
        if not has_column("family", "is_single_parent"):
            conn.exec_driver_sql("ALTER TABLE family ADD COLUMN is_single_parent INTEGER DEFAULT 0")

        conn.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_person_source_line_key ON person (source_id, line_key) WHERE line_key IS NOT NULL"
        )
        conn.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_child_family_person ON child (family_id, person_id)"
        )
        conn.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_family_source_couple ON family (source_id, husband_id, wife_id)"
        )


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
