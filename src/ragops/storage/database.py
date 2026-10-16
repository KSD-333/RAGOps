"""Database — SQLAlchemy engine and session management."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from ragops.core.config import get_settings
from ragops.core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


_engine = None
_session_factory = None


def get_engine():
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        # Use synchronous SQLite for simplicity
        url = settings.database.url.replace("sqlite+aiosqlite", "sqlite")
        _engine = create_engine(url, echo=False)
        logger.info("database_engine_created", url=url)
    return _engine


def get_session_factory():
    """Get or create the session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine())
    return _session_factory


def get_session() -> Session:
    """Get a new database session."""
    return get_session_factory()()


def init_db() -> None:
    """Initialize the database — create all tables."""
    from ragops.storage.models import Base
    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("database_initialized")
