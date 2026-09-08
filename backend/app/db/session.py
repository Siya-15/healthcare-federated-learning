"""SQLAlchemy engine + FastAPI dependency for a short-lived connection."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Connection, Engine

from app.core.config import get_settings

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        if not settings.database_configured:
            raise RuntimeError("DATABASE_URL is not set; cannot create engine")
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5,
            future=True,
        )
    return _engine


def get_db() -> Iterator[Connection]:
    """Yield a connection inside a transaction; commit on success, rollback on error."""
    engine = get_engine()
    with engine.begin() as conn:  # begin() => auto commit / rollback
        yield conn


def ping() -> bool:
    from sqlalchemy import text

    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
