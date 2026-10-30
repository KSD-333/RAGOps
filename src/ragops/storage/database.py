"""Database engine and session management supporting PostgreSQL and SQLite."""

from __future__ import annotations

from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from ragops.core.config import get_settings
from ragops.core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


_engine = None
_session_factory = None
_active_db_type = "sqlite"


def _clean_database_url(raw_url: str) -> str:
    """Normalize database connection URL for SQLAlchemy synchronous engine."""
    url = raw_url.strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and "+psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    elif "sqlite+aiosqlite" in url:
        url = url.replace("sqlite+aiosqlite", "sqlite")
    return url


def get_engine():
    """Get or create the SQLAlchemy database engine with automatic fallback."""
    global _engine, _active_db_type
    if _engine is not None:
        return _engine

    settings = get_settings()
    configured_url = _clean_database_url(settings.database.url)

    # 1. Try configured PostgreSQL or SQLite engine
    try:
        if configured_url.startswith("postgresql"):
            # Fast TCP socket pre-check (250ms) to eliminate 3-5s connection timeout lag if Postgres daemon is stopped
            import socket
            from urllib.parse import urlparse
            parsed = urlparse(configured_url)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or 5432
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.3)
            try:
                sock.connect((host, port))
                sock.close()
            except Exception as sock_err:
                sock.close()
                raise ConnectionError(f"PostgreSQL port {port} on {host} unreachable: {sock_err}")

            logger.info("connecting_to_postgresql", url=configured_url.split("@")[-1])
            _engine = create_engine(
                configured_url,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=1800,
                echo=False,
                connect_args={"connect_timeout": 2},
            )
            # Test connection immediately
            with _engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            _active_db_type = "postgresql"
            logger.info("postgresql_connected_successfully")
            return _engine
        else:
            # SQLite path ensuring directory exists
            if "///" in configured_url:
                db_path = configured_url.split("///")[-1]
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            _engine = create_engine(configured_url, echo=False)
            _active_db_type = "sqlite"
            logger.info("sqlite_database_engine_created", url=configured_url)
            from ragops.storage.models import Base
            Base.metadata.create_all(_engine)
            return _engine

    except Exception as e:
        logger.warning(
            "configured_database_connection_failed_falling_back_to_sqlite",
            error=str(e),
            attempted_url=configured_url.split("@")[-1] if "@" in configured_url else configured_url,
        )
        # Resilient fallback: use local SQLite in ./data/ragops.db
        fallback_dir = Path.cwd() / "data"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        fallback_url = f"sqlite:///{fallback_dir}/ragops.db"
        _engine = create_engine(fallback_url, echo=False)
        _active_db_type = "sqlite_fallback"
        logger.info("using_sqlite_fallback", url=fallback_url)
        from ragops.storage.models import Base
        Base.metadata.create_all(_engine)
        return _engine


def get_session_factory():
    """Get or create the session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


def get_session() -> Session:
    """Get a new database session."""
    return get_session_factory()()


def get_active_db_type() -> str:
    """Return active database engine type ('postgresql', 'sqlite', or 'sqlite_fallback')."""
    global _active_db_type, _engine
    if _engine is None:
        get_engine()
    return _active_db_type


def init_db() -> None:
    """Initialize the database — create all tables and seed default users."""
    from ragops.storage.models import Base, CompanyProfileModel, UserModel
    from ragops.core.auth import DEFAULT_USERS, generate_salt, hash_password

    from sqlalchemy import text
    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("database_tables_verified_or_created", db_type=_active_db_type)

    # Safe schema evolution for existing tables
    try:
        with engine.connect() as conn:
            for col_name, col_type in [
                ("title", "VARCHAR(255) DEFAULT ''"),
                ("doc_type", "VARCHAR(50) DEFAULT 'other'"),
                ("category", "VARCHAR(100) DEFAULT 'General Corporate'"),
                ("is_policy", "BOOLEAN DEFAULT FALSE"),
                ("governance_level", "VARCHAR(50) DEFAULT 'Operational'"),
            ]:
                try:
                    conn.execute(text(f"ALTER TABLE documents ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
                    conn.commit()
                except Exception:
                    conn.rollback()

            for col_name, col_type in [
                ("cache_hit", "BOOLEAN DEFAULT FALSE"),
                ("rewritten_query", "TEXT DEFAULT ''"),
                ("cache_latency_saved_ms", "FLOAT DEFAULT 0.0"),
                ("provider", "VARCHAR(50) DEFAULT 'unknown'"),
            ]:
                try:
                    conn.execute(text(f"ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
                    conn.commit()
                except Exception:
                    conn.rollback()

            for col_name, col_type in [
                ("quarantine", "BOOLEAN DEFAULT FALSE"),
                ("quarantine_reason", "VARCHAR(500) DEFAULT ''"),
            ]:
                try:
                    conn.execute(text(f"ALTER TABLE fact_candidates ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
                    conn.commit()
                except Exception:
                    conn.rollback()
    except Exception as e:
        logger.debug("schema_evolution_check_done", msg=str(e))

    # Seed default dummy users if not present
    session = get_session()
    try:
        for u in DEFAULT_USERS:
            existing = session.query(UserModel).filter(UserModel.username == u["username"]).first()
            if not existing:
                salt = generate_salt()
                pw_hash = hash_password(u["password"], salt)
                user = UserModel(
                    username=u["username"],
                    email=u["email"],
                    password_hash=pw_hash,
                    salt=salt,
                    role=u["role"],
                    is_active=True,
                )
                session.add(user)
        session.commit()
        logger.info("default_dummy_users_seeded", users=[u["username"] for u in DEFAULT_USERS])

        # Seed/sync document catalog from existing Chroma inventory
        try:
            from ragops.storage.models import DocumentModel
            from ragops.ingestion.classifier import DocumentClassifier
            from ragops.retrieval.retriever import RAGRetriever

            retriever = RAGRetriever(use_reranker=False)
            inv = retriever.get_document_inventory()
            synced_count = 0
            for filename in inv:
                existing = session.query(DocumentModel).filter(DocumentModel.source == filename).first()
                classification = DocumentClassifier.classify(filename)
                if not existing:
                    doc_record = DocumentModel(
                        document_id=f"doc_{abs(hash(filename)) % 100000000:08d}",
                        source=filename,
                        title=classification.title,
                        doc_type=classification.doc_type,
                        category=classification.category,
                        is_policy=classification.is_policy,
                        governance_level=classification.governance_level,
                        version="v1",
                        chunk_count=0,
                        metadata_json=classification.to_dict(),
                    )
                    session.add(doc_record)
                    synced_count += 1
                else:
                    existing.title = classification.title
                    existing.doc_type = classification.doc_type
                    existing.category = classification.category
                    existing.is_policy = classification.is_policy
                    existing.governance_level = classification.governance_level
            session.commit()
            logger.info("document_catalog_synced_from_inventory", synced_new=synced_count, total_inventory=len(inv))
        except Exception as e:
            session.rollback()
            logger.warning("document_catalog_sync_failed", error=str(e))

        # Ensure dynamic company profile exists (clean, un-hardcoded)
        try:
            profile = session.query(CompanyProfileModel).first()
            if not profile:
                profile = CompanyProfileModel(
                    company_name="",
                    group_name="",
                    industry="",
                    description="",
                    products=[],
                    employee_details="",
                    locations=[],
                    ceo="",
                    directors=[],
                    domains_urls=[],
                    metadata_json={}
                )
                session.add(profile)
                session.commit()
                logger.info("clean_company_profile_initialized")

                # Embed into Vector Store on initial seeding
                try:
                    from ragops.tools.web_extractor import CompanyWebExtractor
                    CompanyWebExtractor().embed_company_profile(CompanyWebExtractor().repo.get_profile())
                except Exception as emb_err:
                    logger.debug("initial_company_embed_skipped", error=str(emb_err))
        except Exception as e:
            session.rollback()
            logger.warning("company_profile_seed_skipped", error=str(e))

    except Exception as e:
        session.rollback()
        logger.warning("user_seed_skipped_or_failed", error=str(e))
    finally:
        session.close()
