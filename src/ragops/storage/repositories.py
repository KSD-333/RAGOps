"""Repositories — data access layer encapsulating SQL queries."""

from __future__ import annotations

from ragops.core.logging import get_logger
from ragops.storage.database import get_session
from ragops.storage.models import DocumentModel, TraceModel

logger = get_logger(__name__)


class DocumentRepository:
    """Repository for document metadata operations."""

    def save(self, document_id: str, source: str, version: str, chunk_count: int, metadata: dict = None):
        session = get_session()
        try:
            doc = DocumentModel(
                document_id=document_id,
                source=source,
                version=version,
                chunk_count=chunk_count,
                metadata_json=metadata or {},
            )
            session.add(doc)
            session.commit()
            logger.debug("document_saved", document_id=document_id)
        except Exception as e:
            session.rollback()
            logger.error("document_save_failed", error=str(e))
        finally:
            session.close()

    def get_all(self) -> list[dict]:
        session = get_session()
        try:
            docs = session.query(DocumentModel).all()
            return [
                {
                    "document_id": d.document_id,
                    "source": d.source,
                    "version": d.version,
                    "chunk_count": d.chunk_count,
                    "created_at": str(d.created_at),
                }
                for d in docs
            ]
        finally:
            session.close()


class TraceRepository:
    """Repository for trace operations."""

    def save_trace(self, trace_data: dict):
        session = get_session()
        try:
            trace = TraceModel(**trace_data)
            session.add(trace)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error("trace_save_failed", error=str(e))
        finally:
            session.close()

    def get_recent(self, limit: int = 50) -> list[dict]:
        session = get_session()
        try:
            traces = (
                session.query(TraceModel)
                .order_by(TraceModel.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "trace_id": t.trace_id,
                    "query": t.query,
                    "model": t.model,
                    "total_latency_ms": t.total_latency_ms,
                    "created_at": str(t.created_at),
                }
                for t in traces
            ]
        finally:
            session.close()
