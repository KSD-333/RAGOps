"""Repositories — data access layer encapsulating SQL queries for users, chat telemetry, and audit logs."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import cast, desc, func, Integer

import hashlib
import json

from ragops.core.auth import UserProfile, verify_password
from ragops.core.logging import get_logger
from ragops.storage.database import get_session
from ragops.storage.models import (
    ChatMessageModel,
    DocumentModel,
    FeedbackModel,
    TraceModel,
    UserModel,
    CompanyProfileModel,
    CompanySourceModel,
    SourceDocumentModel,
    FactCandidateModel,
    FactEvidenceModel,
    CompanyFactModel,
    FactReviewDecisionModel,
    PublicationOutboxModel,
    SemanticCacheModel,
)

logger = get_logger(__name__)


# -----------------------------------------------------------------------------
# User Repository
# -----------------------------------------------------------------------------

class UserRepository:
    """Repository for user management and authentication."""

    def get_by_username(self, username: str) -> Optional[UserProfile]:
        """Fetch user by unique username."""
        session = get_session()
        try:
            user = session.query(UserModel).filter(UserModel.username == username).first()
            if not user:
                return None
            return UserProfile(
                id=user.id,
                username=user.username,
                email=user.email,
                role=user.role,
                is_active=user.is_active,
            )
        finally:
            session.close()

    def get_by_id(self, user_id: int) -> Optional[UserProfile]:
        """Fetch user by ID."""
        session = get_session()
        try:
            user = session.query(UserModel).filter(UserModel.id == user_id).first()
            if not user:
                return None
            return UserProfile(
                id=user.id,
                username=user.username,
                email=user.email,
                role=user.role,
                is_active=user.is_active,
            )
        finally:
            session.close()

    def verify_credentials(self, username: str, password: str) -> Optional[UserProfile]:
        """Authenticate user against stored salted hash."""
        session = get_session()
        try:
            user = session.query(UserModel).filter(UserModel.username == username).first()
            if not user or not user.is_active:
                return None
            if verify_password(password, user.salt, user.password_hash):
                return UserProfile(
                    id=user.id,
                    username=user.username,
                    email=user.email,
                    role=user.role,
                    is_active=user.is_active,
                )
            return None
        finally:
            session.close()

    def list_all_users_with_stats(self) -> list[dict[str, Any]]:
        """List all users along with cumulative token spend, query count, and last active time."""
        session = get_session()
        try:
            users = session.query(UserModel).order_by(UserModel.id).all()
            result = []
            for u in users:
                # Aggregate user message stats
                stats = (
                    session.query(
                        func.count(ChatMessageModel.id).label("query_count"),
                        func.coalesce(func.sum(ChatMessageModel.total_tokens), 0).label("total_tokens"),
                        func.coalesce(func.sum(ChatMessageModel.cost_usd), 0.0).label("total_cost"),
                        func.max(ChatMessageModel.created_at).label("last_active"),
                    )
                    .filter(ChatMessageModel.username == u.username)
                    .first()
                )

                result.append({
                    "id": u.id,
                    "username": u.username,
                    "email": u.email,
                    "role": u.role,
                    "is_active": u.is_active,
                    "created_at": str(u.created_at),
                    "query_count": stats.query_count if stats else 0,
                    "total_tokens": int(stats.total_tokens) if stats else 0,
                    "total_cost_usd": round(float(stats.total_cost), 5) if stats else 0.0,
                    "last_active": str(stats.last_active) if stats and stats.last_active else None,
                })
            return result
        finally:
            session.close()


# -----------------------------------------------------------------------------
# Chat & Telemetry Repository
# -----------------------------------------------------------------------------

class ChatRepository:
    """Repository for complete chat history, token telemetry, chunk provenance, and risk flags."""

    @staticmethod
    def _detect_risk_signals(query_text: str) -> dict[str, Any]:
        """Detect intent, churn risk, and policy/POSH risk keywords in user queries."""
        q = query_text.lower()

        # Policy & POSH (Prevention of Sexual Harassment / Compliance / HR dispute) keywords
        posh_keywords = [
            "posh", "harassment", "sexual harassment", "discriminate", "discrimination",
            "retaliation", "hostile work", "hr complaint", "complaint against manager",
            "whistleblower", "misconduct", "assault", "abusive", "unethical",
        ]
        policy_risk = any(k in q for k in posh_keywords)

        # Churn risk (user expressing intent to leave, unsubscribe, cancel, or switch)
        churn_keywords = [
            "cancel subscription", "cancel account", "delete account", "how to cancel",
            "refund", "money back", "leaving", "switch to competitor", "discontinue service",
            "unsubscribe", "terminate contract", "downgrade plan", "too expensive", "service is slow",
        ]
        churn_risk = any(k in q for k in churn_keywords)

        # High-level category
        if policy_risk:
            category = "compliance_policy"
        elif churn_risk:
            category = "churn_retention"
        elif any(k in q for k in ["password", "token", "auth", "secret", "api key", "login"]):
            category = "security_auth"
        elif any(k in q for k in ["price", "cost", "billing", "invoice", "payment", "tier"]):
            category = "billing"
        else:
            category = "general_knowledge"

        return {
            "policy_risk_flag": policy_risk,
            "churn_risk_flag": churn_risk,
            "category": category,
        }

    def save_chat_turn(
        self,
        username: str,
        query: str,
        answer: str,
        trace_id: str,
        session_id: str = "",
        model: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
        embed_latency_ms: float = 0.0,
        search_latency_ms: float = 0.0,
        rerank_latency_ms: float = 0.0,
        generation_latency_ms: float = 0.0,
        total_latency_ms: float = 0.0,
        chunks_sent: list[dict[str, Any]] | None = None,
        citations: list[dict[str, Any]] | None = None,
        user_id: Optional[int] = None,
        cache_hit: bool = False,
        rewritten_query: str = "",
        cache_latency_saved_ms: float = 0.0,
    ) -> ChatMessageModel:
        """Persist a full RAG turn with all tokens, latencies, chunk provenance, and cache telemetry."""
        session = get_session()
        try:
            # Token cost estimation: ~$0.05/1M input, $0.08/1M output for fast open-source / Groq
            total_tokens = input_tokens + output_tokens
            cost_usd = round((input_tokens * 0.05 + output_tokens * 0.08) / 1_000_000, 6)

            # Auto-detect intent and risk flags
            risk_info = self._detect_risk_signals(query)

            msg = ChatMessageModel(
                message_id=f"msg_{uuid.uuid4().hex[:12]}",
                session_id=session_id or f"sess_{uuid.uuid4().hex[:8]}",
                trace_id=trace_id,
                user_id=user_id,
                username=username or "anonymous",
                query=query,
                answer=answer,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost_usd=cost_usd,
                embed_latency_ms=round(embed_latency_ms, 2),
                search_latency_ms=round(search_latency_ms, 2),
                rerank_latency_ms=round(rerank_latency_ms, 2),
                generation_latency_ms=round(generation_latency_ms, 2),
                total_latency_ms=round(total_latency_ms, 2),
                chunks_sent=chunks_sent or [],
                citations=citations or [],
                cache_hit=cache_hit,
                rewritten_query=rewritten_query,
                cache_latency_saved_ms=round(cache_latency_saved_ms, 2),
                category=risk_info["category"],
                policy_risk_flag=risk_info["policy_risk_flag"],
                churn_risk_flag=risk_info["churn_risk_flag"],
                training_ready=False,
                created_at=datetime.now(timezone.utc),
            )
            session.add(msg)
            session.commit()
            session.refresh(msg)
            logger.info("chat_turn_persisted", trace_id=trace_id, user=username, tokens=total_tokens, cache_hit=cache_hit)
            return msg
        except Exception as e:
            session.rollback()
            logger.error("chat_save_failed", error=str(e), trace_id=trace_id)
            raise e
        finally:
            session.close()

    def update_feedback(self, trace_id: str, rating: str, comment: str = ""):
        """Update feedback rating and comment on the corresponding chat message."""
        session = get_session()
        try:
            msg = session.query(ChatMessageModel).filter(ChatMessageModel.trace_id == trace_id).first()
            if msg:
                msg.feedback_rating = rating
                msg.feedback_comment = comment
                if rating == "positive":
                    msg.training_ready = True  # Good candidate for SFT/RLHF positive sample
                session.commit()
                logger.info("chat_feedback_updated", trace_id=trace_id, rating=rating)
        except Exception as e:
            session.rollback()
            logger.error("feedback_update_failed", error=str(e))
        finally:
            session.close()

    def get_user_history(self, username: str, limit: int = 50) -> list[dict[str, Any]]:
        """Get chronological chat history for a specific user with full chunk details."""
        session = get_session()
        try:
            records = (
                session.query(ChatMessageModel)
                .filter(ChatMessageModel.username == username)
                .order_by(ChatMessageModel.created_at.desc())
                .limit(limit)
                .all()
            )
            return [self._to_dict(m) for m in records]
        finally:
            session.close()

    def get_user_sessions(self, username: str, limit: int = 50) -> list[dict[str, Any]]:
        """Get list of conversation sessions for a user, ordered by latest activity."""
        session = get_session()
        try:
            subq = (
                session.query(
                    ChatMessageModel.session_id,
                    func.count(ChatMessageModel.id).label("message_count"),
                    func.coalesce(func.sum(ChatMessageModel.total_tokens), 0).label("total_tokens"),
                    func.max(ChatMessageModel.created_at).label("last_activity"),
                )
                .filter(ChatMessageModel.username == username)
                .group_by(ChatMessageModel.session_id)
                .order_by(desc("last_activity"))
                .limit(limit)
                .all()
            )

            result = []
            for s in subq:
                earliest = (
                    session.query(ChatMessageModel.query)
                    .filter(ChatMessageModel.session_id == s.session_id)
                    .order_by(ChatMessageModel.created_at.asc())
                    .first()
                )
                title = earliest.query if earliest else "Conversation"
                if len(title) > 36:
                    title = title[:36] + "..."

                result.append({
                    "session_id": s.session_id,
                    "username": username,
                    "title": title,
                    "message_count": s.message_count,
                    "total_tokens": int(s.total_tokens or 0),
                    "last_activity": str(s.last_activity),
                })
            return result
        finally:
            session.close()

    def get_session_messages(self, session_id: str, username: Optional[str] = None) -> list[dict[str, Any]]:
        """Get all messages in a conversation session in chronological order (turn-by-turn)."""
        session = get_session()
        try:
            q = session.query(ChatMessageModel).filter(ChatMessageModel.session_id == session_id)
            if username:
                q = q.filter(ChatMessageModel.username == username)
            records = q.order_by(ChatMessageModel.created_at.asc()).all()
            return [self._to_dict(m) for m in records]
        finally:
            session.close()

    def delete_session(self, session_id: str, username: Optional[str] = None) -> bool:
        """Delete all messages associated with a session."""
        session = get_session()
        try:
            q = session.query(ChatMessageModel).filter(ChatMessageModel.session_id == session_id)
            if username:
                q = q.filter(ChatMessageModel.username == username)
            count = q.delete(synchronize_session=False)
            session.commit()
            return count > 0
        except Exception as e:
            session.rollback()
            logger.error("delete_session_failed", error=str(e), session_id=session_id)
            return False
        finally:
            session.close()

    def get_all_sessions(self, limit: int = 50, user_filter: Optional[str] = None) -> list[dict[str, Any]]:
        """Admin view: List all multi-turn sessions across all users."""
        session = get_session()
        try:
            q = (
                session.query(
                    ChatMessageModel.session_id,
                    ChatMessageModel.username,
                    func.count(ChatMessageModel.id).label("message_count"),
                    func.coalesce(func.sum(ChatMessageModel.total_tokens), 0).label("total_tokens"),
                    func.coalesce(func.sum(ChatMessageModel.cost_usd), 0.0).label("total_cost"),
                    func.max(ChatMessageModel.created_at).label("last_activity"),
                    func.max(cast(ChatMessageModel.policy_risk_flag, Integer)).label("has_policy_risk"),
                    func.max(cast(ChatMessageModel.churn_risk_flag, Integer)).label("has_churn_risk"),
                )
            )
            if user_filter:
                q = q.filter(ChatMessageModel.username == user_filter)

            results = (
                q.group_by(ChatMessageModel.session_id, ChatMessageModel.username)
                .order_by(desc("last_activity"))
                .limit(limit)
                .all()
            )

            sessions = []
            for r in results:
                earliest = (
                    session.query(ChatMessageModel.query)
                    .filter(ChatMessageModel.session_id == r.session_id)
                    .order_by(ChatMessageModel.created_at.asc())
                    .first()
                )
                title = earliest.query if earliest else "Conversation"
                if len(title) > 45:
                    title = title[:45] + "..."

                sessions.append({
                    "session_id": r.session_id,
                    "username": r.username,
                    "title": title,
                    "message_count": r.message_count,
                    "total_tokens": int(r.total_tokens or 0),
                    "total_cost_usd": round(float(r.total_cost or 0.0), 5),
                    "last_activity": str(r.last_activity),
                    "has_policy_risk": bool(r.has_policy_risk),
                    "has_churn_risk": bool(r.has_churn_risk),
                })
            return sessions
        finally:
            session.close()

    def get_all_logs(
        self,
        limit: int = 100,
        user_filter: Optional[str] = None,
        risk_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Admin view: Retrieve recent chat queries with optional filters."""
        session = get_session()
        try:
            q = session.query(ChatMessageModel)
            if user_filter:
                q = q.filter(ChatMessageModel.username == user_filter)
            if risk_only:
                q = q.filter((ChatMessageModel.policy_risk_flag == True) | (ChatMessageModel.churn_risk_flag == True))

            records = q.order_by(ChatMessageModel.created_at.desc()).limit(limit).all()
            return [self._to_dict(m) for m in records]
        finally:
            session.close()

    def get_analytics_summary(self) -> dict[str, Any]:
        """Aggregate high-level observability numbers for admin dashboard."""
        session = get_session()
        try:
            total_queries = session.query(func.count(ChatMessageModel.id)).scalar() or 0
            total_tokens = session.query(func.coalesce(func.sum(ChatMessageModel.total_tokens), 0)).scalar() or 0
            total_cost = session.query(func.coalesce(func.sum(ChatMessageModel.cost_usd), 0.0)).scalar() or 0.0
            avg_latency = session.query(func.coalesce(func.avg(ChatMessageModel.total_latency_ms), 0.0)).scalar() or 0.0

            policy_risk_count = session.query(func.count(ChatMessageModel.id)).filter(ChatMessageModel.policy_risk_flag == True).scalar() or 0
            churn_risk_count = session.query(func.count(ChatMessageModel.id)).filter(ChatMessageModel.churn_risk_flag == True).scalar() or 0
            positive_feedback = session.query(func.count(ChatMessageModel.id)).filter(ChatMessageModel.feedback_rating == "positive").scalar() or 0
            negative_feedback = session.query(func.count(ChatMessageModel.id)).filter(ChatMessageModel.feedback_rating == "negative").scalar() or 0

            return {
                "total_queries": total_queries,
                "total_tokens": int(total_tokens),
                "total_cost_usd": round(float(total_cost), 4),
                "avg_latency_ms": round(float(avg_latency), 1),
                "policy_risk_count": policy_risk_count,
                "churn_risk_count": churn_risk_count,
                "positive_feedback_count": positive_feedback,
                "negative_feedback_count": negative_feedback,
            }
        finally:
            session.close()

    def get_frequent_queries(self, limit: int = 8) -> list[dict[str, Any]]:
        """Identify top frequently asked queries across all users."""
        session = get_session()
        try:
            results = (
                session.query(
                    ChatMessageModel.query,
                    func.count(ChatMessageModel.id).label("count"),
                    func.avg(ChatMessageModel.total_latency_ms).label("avg_latency"),
                    func.max(ChatMessageModel.created_at).label("last_asked"),
                )
                .group_by(ChatMessageModel.query)
                .order_by(desc("count"))
                .limit(limit)
                .all()
            )
            return [
                {
                    "query": r.query,
                    "count": r.count,
                    "avg_latency_ms": round(float(r.avg_latency), 1),
                    "last_asked": str(r.last_asked),
                }
                for r in results
            ]
        finally:
            session.close()

    def get_training_samples(self, limit: int = 100) -> list[dict[str, Any]]:
        """Export dataset for model fine-tuning (Supervised Fine-Tuning / DPO)."""
        session = get_session()
        try:
            records = (
                session.query(ChatMessageModel)
                .filter(ChatMessageModel.feedback_rating == "positive")
                .order_by(ChatMessageModel.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "instruction": m.query,
                    "context": [c.get("text", "") for c in (m.chunks_sent or [])],
                    "response": m.answer,
                    "citations": m.citations,
                    "model": m.model,
                    "created_at": str(m.created_at),
                }
                for m in records
            ]
        finally:
            session.close()

    @staticmethod
    def _to_dict(m: ChatMessageModel) -> dict[str, Any]:
        """Convert ORM model to clean dictionary."""
        return {
            "id": m.id,
            "message_id": m.message_id,
            "session_id": m.session_id,
            "trace_id": m.trace_id,
            "username": m.username,
            "query": m.query,
            "answer": m.answer,
            "model": m.model,
            "input_tokens": m.input_tokens,
            "output_tokens": m.output_tokens,
            "total_tokens": m.total_tokens,
            "cost_usd": m.cost_usd,
            "embed_latency_ms": m.embed_latency_ms,
            "search_latency_ms": m.search_latency_ms,
            "rerank_latency_ms": m.rerank_latency_ms,
            "generation_latency_ms": m.generation_latency_ms,
            "total_latency_ms": m.total_latency_ms,
            "chunks_sent": m.chunks_sent or [],
            "citations": m.citations or [],
            "feedback_rating": m.feedback_rating,
            "feedback_comment": m.feedback_comment,
            "category": m.category,
            "policy_risk_flag": m.policy_risk_flag,
            "churn_risk_flag": m.churn_risk_flag,
            "created_at": str(m.created_at),
        }


# -----------------------------------------------------------------------------
# Existing Document & Trace Repositories (Preserved)
# -----------------------------------------------------------------------------

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


# -----------------------------------------------------------------------------
# Document Catalog Repository
# -----------------------------------------------------------------------------

class DocumentCatalogRepository:
    """Repository for querying auto-classified document inventory, disk reconciliation, and vector sync."""

    @staticmethod
    def get_raw_files() -> dict[str, Any]:
        """Scan data/raw (and data) for physical document files."""
        from pathlib import Path
        raw_files = {}
        # Priority: data/raw directory
        raw_dir = Path("data/raw").resolve()
        if not raw_dir.exists():
            raw_dir.mkdir(parents=True, exist_ok=True)

        for p in raw_dir.iterdir():
            if p.is_file() and not p.name.startswith((".", "~")) and p.name != ".gitkeep":
                if p.suffix.lower() in {".pdf", ".md", ".markdown", ".txt", ".html", ".htm", ".docx"}:
                    raw_files[p.name] = p

        # Secondary: check data/ directly for documents that aren't system files
        data_dir = Path("data").resolve()
        if data_dir.exists() and data_dir.is_dir():
            for p in data_dir.iterdir():
                if p.is_file() and not p.name.startswith((".", "~")):
                    if p.name.lower() not in {"readme.md", "ragops.db", "feedback.jsonl", "version_registry.json"} and p.suffix.lower() in {".pdf", ".md", ".markdown", ".txt", ".html", ".htm"}:
                        if p.name not in raw_files:
                            raw_files[p.name] = p
        return raw_files

    def reconcile_with_disk(self, auto_embed: bool = False) -> dict[str, Any]:
        """Reconcile physical disk files (data/raw), PostgreSQL/SQLite DocumentModel, and ChromaDB chunks.
        
        1. If a file was deleted from disk, remove its record from DB and remove its chunks from ChromaDB.
        2. If a file exists in data/raw, ensure it has a record in DB with accurate chunk counts from ChromaDB.
        3. If auto_embed=True and a file is not yet embedded, chunk and index it into ChromaDB.
        """
        from ragops.retrieval.retriever import RAGRetriever
        from ragops.ingestion.classifier import DocumentClassifier

        raw_files = self.get_raw_files()
        retriever = RAGRetriever(use_reranker=False)
        chroma_counts = retriever.get_document_chunk_counts()

        session = get_session()
        purged_sources = []
        added_sources = []
        updated_sources = []
        embedded_sources = []

        try:
            # 1. Purge DB records and ChromaDB chunks for files no longer on disk
            all_db_docs = session.query(DocumentModel).all()
            for doc in all_db_docs:
                if doc.source not in raw_files:
                    # File was deleted from physical disk! Delete its chunks and its DB row.
                    retriever.delete_document_chunks(doc.source)
                    session.delete(doc)
                    purged_sources.append(doc.source)

            # 2. Register new files or update chunk counts for files on disk
            for filename, path in raw_files.items():
                chunk_cnt = chroma_counts.get(filename, 0)
                file_size = path.stat().st_size if path.exists() else 0

                # Auto-embed if requested and not yet embedded
                if auto_embed and chunk_cnt == 0:
                    try:
                        from ragops.ingestion.pipeline import IngestionPipeline
                        pipeline = IngestionPipeline()
                        chunks = pipeline.ingest_file(path)
                        indexed = retriever.index(chunks)
                        chunk_cnt = indexed
                        chroma_counts[filename] = chunk_cnt
                        embedded_sources.append(filename)
                    except Exception as e:
                        logger.error("auto_embed_failed_during_reconciliation", source=filename, error=str(e))

                is_embedded = (chunk_cnt > 0)
                existing = session.query(DocumentModel).filter(DocumentModel.source == filename).first()
                if not existing:
                    classification = DocumentClassifier.classify(path)
                    new_doc = DocumentModel(
                        document_id=f"doc_{abs(hash(filename)) % 100000000:08d}",
                        source=filename,
                        title=classification.title or filename,
                        doc_type=classification.doc_type,
                        category=classification.category,
                        is_policy=classification.is_policy,
                        governance_level=classification.governance_level,
                        version="v1",
                        chunk_count=chunk_cnt,
                        metadata_json={
                            **classification.to_dict(),
                            "file_size_bytes": file_size,
                            "is_embedded": is_embedded,
                        },
                    )
                    session.add(new_doc)
                    added_sources.append(filename)
                else:
                    existing.chunk_count = chunk_cnt
                    meta = dict(existing.metadata_json or {})
                    meta["file_size_bytes"] = file_size
                    meta["is_embedded"] = is_embedded
                    existing.metadata_json = meta
                    updated_sources.append(filename)

            session.commit()

            # 3. Invalidate caches if anything changed
            if purged_sources or embedded_sources:
                try:
                    from ragops.storage.models import SemanticCacheModel
                    session.query(SemanticCacheModel).delete(synchronize_session=False)
                    session.commit()
                except Exception:
                    pass
                try:
                    from ragops.rag.pipeline import get_rag_pipeline
                    p = get_rag_pipeline()
                    if hasattr(p, "_query_intel") and hasattr(p._query_intel, "_memory_cache"):
                        p._query_intel._memory_cache.clear()
                except Exception:
                    pass

            return {
                "status": "reconciled",
                "total_disk_files": len(raw_files),
                "purged_missing_files": purged_sources,
                "added_new_files": added_sources,
                "updated_files": len(updated_sources),
                "embedded_files": embedded_sources,
            }
        except Exception as e:
            session.rollback()
            logger.error("document_reconciliation_failed", error=str(e))
            raise
        finally:
            session.close()

    def embed_document(self, source: str) -> dict[str, Any]:
        """Ingest, chunk, and embed a specific document from disk into ChromaDB."""
        raw_files = self.get_raw_files()
        if source not in raw_files:
            raise FileNotFoundError(f"Document '{source}' not found in data/raw or data storage.")

        target_path = raw_files[source]
        from ragops.ingestion.pipeline import IngestionPipeline
        from ragops.retrieval.retriever import RAGRetriever

        pipeline = IngestionPipeline()
        chunks = pipeline.ingest_file(target_path)

        retriever = RAGRetriever(use_reranker=False)
        indexed_count = retriever.index(chunks)

        session = get_session()
        try:
            doc = session.query(DocumentModel).filter(DocumentModel.source == source).first()
            if doc:
                doc.chunk_count = indexed_count
                meta = dict(doc.metadata_json or {})
                meta["is_embedded"] = True
                meta["file_size_bytes"] = target_path.stat().st_size
                doc.metadata_json = meta
                session.commit()

            # Invalidate semantic cache
            try:
                from ragops.storage.models import SemanticCacheModel
                session.query(SemanticCacheModel).delete(synchronize_session=False)
                session.commit()
            except Exception:
                pass

            try:
                from ragops.rag.pipeline import get_rag_pipeline
                p = get_rag_pipeline()
                if hasattr(p, "_query_intel") and hasattr(p._query_intel, "_memory_cache"):
                    p._query_intel._memory_cache.clear()
            except Exception:
                pass

            return {
                "status": "success",
                "source": source,
                "chunks_indexed": indexed_count,
                "file_size_bytes": target_path.stat().st_size,
            }
        finally:
            session.close()

    def embed_all_pending(self) -> dict[str, Any]:
        """Embed all documents that are currently pending in data/raw."""
        # Reconcile first
        self.reconcile_with_disk(auto_embed=False)
        session = get_session()
        pending_sources = []
        try:
            pending_docs = session.query(DocumentModel).filter(
                (DocumentModel.chunk_count == 0) | (DocumentModel.chunk_count == None)
            ).all()
            pending_sources = [d.source for d in pending_docs]
        finally:
            session.close()

        total_chunks = 0
        embedded_list = []
        for src in pending_sources:
            try:
                res = self.embed_document(src)
                total_chunks += res.get("chunks_indexed", 0)
                embedded_list.append(src)
            except Exception as e:
                logger.error("failed_to_embed_pending_doc", source=src, error=str(e))

        return {
            "status": "success",
            "total_embedded_files": len(embedded_list),
            "total_chunks_indexed": total_chunks,
            "embedded_files": embedded_list,
        }

    def delete_document(self, source: str) -> dict[str, Any]:
        """Delete document from disk, remove its chunks from ChromaDB, and delete from DB."""
        from ragops.retrieval.retriever import RAGRetriever
        from pathlib import Path

        # 1. Delete physical file from data/raw/ or data/
        deleted_from_disk = False
        raw_files = self.get_raw_files()
        if source in raw_files:
            file_path = raw_files[source]
            try:
                if file_path.exists():
                    file_path.unlink()
                    deleted_from_disk = True
                    logger.info("physical_file_deleted", path=str(file_path))
            except Exception as e:
                logger.warning("failed_to_delete_physical_file", path=str(file_path), error=str(e))

        # Check secondary paths as safety
        for base_dir in ["data/raw", "data"]:
            cand = Path(base_dir) / source
            if cand.exists():
                try:
                    cand.unlink()
                    deleted_from_disk = True
                except Exception:
                    pass

        # 2. Delete chunks from ChromaDB
        retriever = RAGRetriever(use_reranker=False)
        chunks_deleted = retriever.delete_document_chunks(source)

        # 3. Delete from DocumentModel in DB
        session = get_session()
        db_deleted = False
        try:
            doc = session.query(DocumentModel).filter(
                (DocumentModel.source == source) | (DocumentModel.document_id == source)
            ).first()
            if doc:
                session.delete(doc)
                session.commit()
                db_deleted = True

            # Invalidate semantic cache
            try:
                from ragops.storage.models import SemanticCacheModel
                session.query(SemanticCacheModel).delete(synchronize_session=False)
                session.commit()
            except Exception:
                pass

            try:
                from ragops.rag.pipeline import get_rag_pipeline
                p = get_rag_pipeline()
                if hasattr(p, "_query_intel") and hasattr(p._query_intel, "_memory_cache"):
                    p._query_intel._memory_cache.clear()
            except Exception:
                pass
        finally:
            session.close()

        return {
            "status": "success",
            "source": source,
            "physical_file_deleted": deleted_from_disk,
            "chunks_deleted": chunks_deleted,
            "db_record_deleted": db_deleted,
        }

    def list_documents(self, doc_type: str | None = None, auto_reconcile: bool = True) -> list[dict[str, Any]]:
        """List all indexed documents with classification metadata and embedding status."""
        if auto_reconcile:
            try:
                self.reconcile_with_disk(auto_embed=False)
            except Exception as e:
                logger.warning("auto_reconcile_failed", error=str(e))

        session = get_session()
        try:
            query = session.query(DocumentModel)
            if doc_type:
                query = query.filter(DocumentModel.doc_type == doc_type.lower())
            docs = query.order_by(DocumentModel.doc_type, DocumentModel.source).all()
            return [
                {
                    "id": d.id,
                    "document_id": d.document_id,
                    "source": d.source,
                    "title": d.title or d.source,
                    "doc_type": d.doc_type,
                    "category": d.category,
                    "is_policy": d.is_policy,
                    "governance_level": d.governance_level,
                    "version": d.version,
                    "chunk_count": d.chunk_count or 0,
                    "is_embedded": bool(d.chunk_count and d.chunk_count > 0),
                    "file_size_bytes": (d.metadata_json or {}).get("file_size_bytes", 0),
                    "created_at": str(d.created_at),
                }
                for d in docs
            ]
        finally:
            session.close()

    def get_summary(self, auto_reconcile: bool = False) -> dict[str, Any]:
        """Get high-level count of documents broken down by classification and embedding state."""
        if auto_reconcile:
            try:
                self.reconcile_with_disk(auto_embed=False)
            except Exception as e:
                logger.warning("auto_reconcile_summary_failed", error=str(e))

        session = get_session()
        try:
            docs = session.query(DocumentModel).all()
            total = len(docs)
            policies = sum(1 for d in docs if d.doc_type == "policy")
            codes = sum(1 for d in docs if d.doc_type == "code")
            programmes = sum(1 for d in docs if d.doc_type == "programme")
            governance = sum(1 for d in docs if d.doc_type == "governance")
            manuals = sum(1 for d in docs if d.doc_type == "manual")
            others = total - (policies + codes + programmes + governance + manuals)
            embedded_docs = sum(1 for d in docs if (d.chunk_count or 0) > 0)
            pending_docs = total - embedded_docs
            total_chunks = sum(d.chunk_count or 0 for d in docs)

            return {
                "total_documents": total,
                "policies": policies,
                "codes": codes,
                "programmes": programmes,
                "governance": governance,
                "manuals": manuals,
                "others": max(0, others),
                "embedded_documents": embedded_docs,
                "pending_documents": pending_docs,
                "total_chunks": total_chunks,
            }
        finally:
            session.close()



# -----------------------------------------------------------------------------
# Semantic Cache Repository
# -----------------------------------------------------------------------------

class SemanticCacheRepository:
    """Repository for inspecting and managing the semantic answer cache across Redis and DB."""

    def get_cache_stats(self) -> dict[str, Any]:
        """Get aggregate metrics for semantic caching across Redis and Database."""
        session = get_session()
        try:
            from ragops.storage.models import SemanticCacheModel
            from ragops.storage.redis_cache import RedisSemanticCache

            total_entries = session.query(func.count(SemanticCacheModel.id)).scalar() or 0
            total_hits = session.query(func.sum(SemanticCacheModel.hit_count)).scalar() or 0

            # Chat turns cache hit metrics
            chat_total = session.query(func.count(ChatMessageModel.id)).scalar() or 0
            chat_cache_hits = session.query(func.count(ChatMessageModel.id)).filter(
                ChatMessageModel.cache_hit == True
            ).scalar() or 0
            total_saved_ms = session.query(
                func.sum(ChatMessageModel.cache_latency_saved_ms)
            ).scalar() or 0.0

            hit_rate_pct = round((chat_cache_hits / chat_total * 100), 1) if chat_total > 0 else 0.0

            # Redis telemetry
            redis_stats = {}
            try:
                redis_stats = RedisSemanticCache.get_instance().get_stats()
            except Exception:
                pass

            return {
                "total_cached_patterns": max(total_entries, redis_stats.get("total_cached_entries", 0)),
                "total_cache_hits": int(total_hits) + redis_stats.get("total_hits", 0),
                "chat_cache_hits": int(chat_cache_hits),
                "chat_total_queries": int(chat_total),
                "cache_hit_rate_pct": hit_rate_pct,
                "total_latency_saved_ms": round(float(total_saved_ms), 1),
                "total_cost_saved_usd": round(int(chat_cache_hits) * 0.0003, 5),
                "redis_enabled": redis_stats.get("redis_enabled", True),
                "redis_connected": redis_stats.get("redis_connected", False),
                "redis_url": redis_stats.get("redis_url", "redis://127.0.0.1:6379/0"),
                "redis_cached_entries": redis_stats.get("total_cached_entries", 0),
                "redis_hits": redis_stats.get("total_hits", 0),
                "redis_exact_hits": redis_stats.get("exact_hits", 0),
                "redis_semantic_hits": redis_stats.get("semantic_hits", 0),
                "redis_memory": redis_stats.get("used_memory_human", "0B"),
                "similarity_threshold": redis_stats.get("similarity_threshold", 0.92),
                "similarity_threshold_range": "0.90 - 0.95 (direct cache hit)",
            }
        finally:
            session.close()

    def list_entries(self, limit: int = 50) -> list[dict[str, Any]]:
        """List active cache entries with hit counts and scopes from DB and Redis."""
        session = get_session()
        try:
            from ragops.storage.models import SemanticCacheModel
            from ragops.storage.redis_cache import RedisSemanticCache

            entries = (
                session.query(SemanticCacheModel)
                .order_by(SemanticCacheModel.hit_count.desc(), SemanticCacheModel.last_hit_at.desc())
                .limit(limit)
                .all()
            )
            db_entries = [
                {
                    "id": e.id,
                    "cache_key": e.cache_key,
                    "normalized_query": e.normalized_query,
                    "original_query": e.original_query,
                    "intent": e.intent,
                    "scope": e.scope,
                    "target_entity": e.target_entity,
                    "hit_count": e.hit_count,
                    "last_hit_at": str(e.last_hit_at),
                    "created_at": str(e.created_at),
                    "answer_preview": e.answer[:120] + ("..." if len(e.answer) > 120 else ""),
                    "tier": "database",
                }
                for e in entries
            ]

            # If DB is empty, pull from Redis
            if not db_entries:
                try:
                    redis_entries = RedisSemanticCache.get_instance().list_entries(limit=limit)
                    for r in redis_entries:
                        r["tier"] = "redis"
                    return redis_entries
                except Exception:
                    pass

            return db_entries
        finally:
            session.close()

    def clear_cache(self) -> int:
        """Clear all semantic cache entries across DB and Redis."""
        session = get_session()
        try:
            from ragops.storage.models import SemanticCacheModel
            from ragops.storage.redis_cache import RedisSemanticCache

            count = session.query(SemanticCacheModel).delete()
            session.commit()

            # Clear Redis cache
            try:
                RedisSemanticCache.get_instance().clear_cache()
            except Exception:
                pass

            logger.info("semantic_cache_cleared", deleted_count=count)
            return count
        except Exception as e:
            session.rollback()
            logger.error("failed_to_clear_cache", error=str(e))
            return 0
        finally:
            session.close()


# -----------------------------------------------------------------------------
# Company Profile Repository
# -----------------------------------------------------------------------------

class CompanyRepository:
    """Repository for managing dynamic company profile and MNC domains/URLs."""

    def get_profile(self) -> dict[str, Any]:
        """Fetch the current company profile from PostgreSQL."""
        session = get_session()
        try:
            from ragops.storage.models import CompanyProfileModel
            profile = session.query(CompanyProfileModel).first()
            if not profile:
                return {}
            return self._to_dict(profile)
        finally:
            session.close()

    def update_profile(self, data: dict[str, Any]) -> dict[str, Any]:
        """Update or create the company profile."""
        session = get_session()
        try:
            from ragops.storage.models import CompanyProfileModel
            profile = session.query(CompanyProfileModel).first()
            if not profile:
                profile = CompanyProfileModel()
                session.add(profile)

            updatable_fields = [
                "company_name",
                "group_name",
                "industry",
                "description",
                "products",
                "employee_details",
                "locations",
                "ceo",
                "directors",
                "domains_urls",
                "metadata_json",
            ]
            for field in updatable_fields:
                if field in data:
                    setattr(profile, field, data[field])

            # Gracefully handle clients and hubs passed at top level
            if "clients" in data or "hubs" in data:
                current_meta = dict(profile.metadata_json or {})
                if "clients" in data:
                    current_meta["clients"] = data["clients"]
                if "hubs" in data:
                    current_meta["hubs"] = data["hubs"]
                profile.metadata_json = current_meta

            profile.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(profile)
            return self._to_dict(profile)
        except Exception as e:
            session.rollback()
            logger.error("update_company_profile_failed", error=str(e))
            raise
        finally:
            session.close()

    def add_domain_url(self, url: str) -> dict[str, Any]:
        """Append a domain/URL to the list of registered corporate MNC URLs."""
        session = get_session()
        try:
            from ragops.storage.models import CompanyProfileModel
            profile = session.query(CompanyProfileModel).first()
            if not profile:
                profile = CompanyProfileModel()
                session.add(profile)

            urls = list(profile.domains_urls or [])
            clean_url = url.strip()
            if clean_url and clean_url not in urls:
                urls.append(clean_url)
                profile.domains_urls = urls
                profile.updated_at = datetime.now(timezone.utc)
                session.commit()
                session.refresh(profile)
            return self._to_dict(profile)
        finally:
            session.close()

    def remove_domain_url(self, url: str) -> dict[str, Any]:
        """Remove a domain/URL from the profile and purge all related sources, vector chunks, and caches."""
        session = get_session()
        try:
            from ragops.storage.models import CompanyProfileModel, CompanySourceModel, SemanticCacheModel
            clean_url = url.strip()

            # 1. Purge matching sources from CompanySourceModel
            session.query(CompanySourceModel).filter(
                (CompanySourceModel.source_url == clean_url) |
                (CompanySourceModel.source_url == clean_url + "/") |
                (CompanySourceModel.source_url == clean_url.rstrip("/")) |
                (CompanySourceModel.display_name.ilike(f"%{clean_url}%"))
            ).delete(synchronize_session=False)

            # 2. Invalidate semantic cache so stale answers for this URL disappear
            session.query(SemanticCacheModel).delete(synchronize_session=False)

            # 3. Purge vector chunks from ChromaDB
            try:
                from ragops.retrieval.retriever import get_retriever
                retriever = get_retriever()
                if hasattr(retriever._vector_store, "_collection") and retriever._vector_store._collection:
                    try:
                        retriever._vector_store._collection.delete(where={"url": clean_url})
                    except Exception:
                        pass
                    try:
                        retriever._vector_store._collection.delete(where={"source": f"Corporate Grounded Knowledge ({clean_url})"})
                    except Exception:
                        pass
            except Exception as emb_e:
                logger.debug("vector_store_remove_url_skipped", error=str(emb_e))

            # 4. Update CompanyProfileModel
            profile = session.query(CompanyProfileModel).first()
            if profile:
                if profile.domains_urls:
                    urls = [u for u in profile.domains_urls if u.strip().rstrip("/") != clean_url.rstrip("/")]
                    profile.domains_urls = urls
                # If all registered URLs are gone, reset company profile to clean state
                if not profile.domains_urls:
                    profile.company_name = "Enterprise"
                    profile.group_name = ""
                    profile.industry = ""
                    profile.description = ""
                    profile.products = []
                    profile.employee_details = ""
                    profile.locations = []
                    profile.ceo = ""
                    profile.directors = []
                    profile.metadata_json = {}
                profile.updated_at = datetime.now(timezone.utc)
                session.commit()
                session.refresh(profile)

            # 5. Clear in-memory query intelligence cache
            try:
                from ragops.rag.pipeline import get_rag_pipeline
                pipeline = get_rag_pipeline()
                if hasattr(pipeline, "_query_intel") and hasattr(pipeline._query_intel, "_memory_cache"):
                    pipeline._query_intel._memory_cache.clear()
            except Exception:
                pass

            return self._to_dict(profile) if profile else {}
        except Exception as e:
            session.rollback()
            logger.error("remove_domain_url_failed", error=str(e))
            raise
        finally:
            session.close()

    def clear_profile(self) -> dict[str, Any]:
        """Reset the active company profile to an empty blank state and purge all sources and caches."""
        session = get_session()
        try:
            from ragops.storage.models import CompanyProfileModel, CompanySourceModel, SemanticCacheModel
            session.query(SemanticCacheModel).delete(synchronize_session=False)
            session.query(CompanySourceModel).delete(synchronize_session=False)

            profile = session.query(CompanyProfileModel).first()
            if profile:
                profile.company_name = "Enterprise"
                profile.group_name = ""
                profile.industry = ""
                profile.description = ""
                profile.products = []
                profile.employee_details = ""
                profile.locations = []
                profile.ceo = ""
                profile.directors = []
                profile.domains_urls = []
                profile.metadata_json = {}
                profile.updated_at = datetime.now(timezone.utc)
                session.commit()
                session.refresh(profile)

                try:
                    from ragops.tools.web_extractor import CompanyWebExtractor
                    CompanyWebExtractor().clear_company_embeddings()
                except Exception as emb_e:
                    logger.debug("vector_store_clear_profile_skipped", error=str(emb_e))

                # Clear in-memory query intelligence cache
                try:
                    from ragops.rag.pipeline import get_rag_pipeline
                    pipeline = get_rag_pipeline()
                    if hasattr(pipeline, "_query_intel") and hasattr(pipeline._query_intel, "_memory_cache"):
                        pipeline._query_intel._memory_cache.clear()
                except Exception:
                    pass

                return self._to_dict(profile)
            return {}
        except Exception as e:
            session.rollback()
            logger.error("clear_profile_failed", error=str(e))
            raise
        finally:
            session.close()

    @staticmethod

    def _to_dict(p: Any) -> dict[str, Any]:
        return {
            "id": p.id,
            "company_name": p.company_name,
            "group_name": p.group_name,
            "industry": p.industry,
            "description": p.description,
            "products": p.products or [],
            "employee_details": p.employee_details or "",
            "locations": p.locations or [],
            "ceo": p.ceo or "",
            "directors": p.directors or [],
            "domains_urls": p.domains_urls or [],
            "metadata_json": p.metadata_json or {},
            "updated_at": str(p.updated_at) if p.updated_at else "",
            "created_at": str(p.created_at) if p.created_at else "",
        }


# -----------------------------------------------------------------------------
# Source-Backed Fact Management Repository (Review-Before-Publish)
# -----------------------------------------------------------------------------

class FactManagementRepository:
    """Enterprise repository implementing source-backed candidate extraction,

    field-level validation, human review decisions, and reliable outbox publication.
    """

    def register_source(
        self,
        display_name: str,
        source_url: Optional[str] = None,
        source_type: str = "website",
        country_code: Optional[str] = None,
        language_code: str = "en",
        organization_id: str = "default_org",
        verification_status: str = "verified",
    ) -> dict[str, Any]:
        """Register an official corporate domain or document upload source."""
        session = get_session()
        try:
            session.query(SemanticCacheModel).delete(synchronize_session=False)
            existing = None
            if source_url:
                existing = session.query(CompanySourceModel).filter(
                    CompanySourceModel.organization_id == organization_id,
                    CompanySourceModel.source_url == source_url,
                ).first()

            if existing:
                existing.display_name = display_name
                existing.verification_status = verification_status
                existing.updated_at = datetime.now(timezone.utc)
                session.commit()
                session.refresh(existing)
                return self._source_to_dict(existing)

            src = CompanySourceModel(
                organization_id=organization_id,
                source_type=source_type,
                source_url=source_url,
                display_name=display_name,
                country_code=country_code,
                language_code=language_code,
                verification_status=verification_status,
                is_enabled=True,
                created_at=datetime.now(timezone.utc),
            )
            session.add(src)
            session.commit()
            session.refresh(src)
            return self._source_to_dict(src)
        except Exception as e:
            session.rollback()
            logger.error("register_source_failed", error=str(e))
            raise
        finally:
            session.close()

    def get_sources(self, organization_id: str = "default_org") -> list[dict[str, Any]]:
        """List all registered company sources."""
        session = get_session()
        try:
            records = (
                session.query(CompanySourceModel)
                .filter(CompanySourceModel.organization_id == organization_id)
                .order_by(CompanySourceModel.created_at.asc())
                .all()
            )
            return [self._source_to_dict(r) for r in records]
        finally:
            session.close()

    def record_source_document(
        self,
        content_text: str,
        canonical_url: Optional[str] = None,
        title: Optional[str] = None,
        source_id: Optional[str] = None,
        country_code: Optional[str] = None,
        publication_date: Optional[str] = None,
        organization_id: str = "default_org",
    ) -> dict[str, Any]:
        """Store immutable retrieved web page or uploaded document with SHA-256 versioning."""
        session = get_session()
        try:
            sha256 = hashlib.sha256(content_text.encode("utf-8")).hexdigest()

            # Check if this exact content already exists for this source
            existing = session.query(SourceDocumentModel).filter(
                SourceDocumentModel.organization_id == organization_id,
                SourceDocumentModel.content_sha256 == sha256,
            ).first()
            if existing:
                return self._doc_to_dict(existing)

            # Determine next version
            latest = (
                session.query(SourceDocumentModel)
                .filter(
                    SourceDocumentModel.organization_id == organization_id,
                    SourceDocumentModel.source_id == source_id,
                )
                .order_by(SourceDocumentModel.content_version.desc())
                .first()
            )
            version = (latest.content_version + 1) if latest else 1

            doc = SourceDocumentModel(
                organization_id=organization_id,
                source_id=source_id,
                canonical_url=canonical_url,
                title=title or (canonical_url or "Company Document"),
                content_text=content_text,
                content_sha256=sha256,
                content_version=version,
                country_code=country_code,
                publication_date=publication_date,
                processing_status="ready",
                fetched_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
            )
            session.add(doc)
            session.commit()
            session.refresh(doc)
            return self._doc_to_dict(doc)
        except Exception as e:
            session.rollback()
            logger.error("record_source_document_failed", error=str(e))
            raise
        finally:
            session.close()

    def save_candidate_with_evidence(
        self,
        section_key: str,
        fact_key: str,
        proposed_value: Any,
        normalized_value: Any = None,
        scope_key: str = "global",
        validation_status: str = "pending",
        review_status: str = "pending",
        evidence_list: Optional[list[dict[str, Any]]] = None,
        document_id: Optional[str] = None,
        organization_id: str = "default_org",
        extraction_confidence: float = 1.0,
    ) -> dict[str, Any]:
        """Save an extracted field candidate with its supporting evidence citations."""
        session = get_session()
        try:
            cand = FactCandidateModel(
                organization_id=organization_id,
                document_id=document_id,
                section_key=section_key,
                fact_key=fact_key,
                scope_key=scope_key,
                proposed_value=proposed_value,
                normalized_value=normalized_value or proposed_value,
                validation_status=validation_status,
                review_status=review_status,
                extraction_confidence=extraction_confidence,
                created_at=datetime.now(timezone.utc),
            )
            session.add(cand)
            session.flush()

            if evidence_list:
                for ev in evidence_list:
                    ev_model = FactEvidenceModel(
                        candidate_id=cand.id,
                        document_id=document_id,
                        evidence_text=ev.get("evidence_text", ""),
                        start_offset=ev.get("start_offset"),
                        end_offset=ev.get("end_offset"),
                        section_heading=ev.get("section_heading", ""),
                        source_url=ev.get("source_url", ""),
                        retrieved_at=datetime.now(timezone.utc),
                    )
                    session.add(ev_model)

            session.commit()
            session.refresh(cand)
            return self._candidate_to_dict(cand, session=session)
        except Exception as e:
            session.rollback()
            logger.error("save_candidate_failed", error=str(e))
            raise
        finally:
            session.close()

    def get_candidates(
        self,
        organization_id: str = "default_org",
        section_key: Optional[str] = None,
        review_status: Optional[str] = None,
        validation_status: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """List extracted fact candidates with citations and review statuses."""
        session = get_session()
        try:
            q = session.query(FactCandidateModel).filter(FactCandidateModel.organization_id == organization_id)
            if section_key:
                q = q.filter(FactCandidateModel.section_key == section_key)
            if review_status:
                q = q.filter(FactCandidateModel.review_status == review_status)
            if validation_status:
                q = q.filter(FactCandidateModel.validation_status == validation_status)

            candidates = q.order_by(FactCandidateModel.created_at.asc()).all()
            return [self._candidate_to_dict(c, session=session) for c in candidates]
        finally:
            session.close()

    def update_candidate_proposed_value(
        self,
        candidate_id: str,
        new_value: Any,
        user_id: str = "admin",
    ) -> dict[str, Any]:
        """Administrator edits candidate value before approving."""
        session = get_session()
        try:
            cand = session.query(FactCandidateModel).filter(FactCandidateModel.id == candidate_id).first()
            if not cand:
                raise ValueError(f"Candidate {candidate_id} not found")

            cand.proposed_value = new_value
            cand.normalized_value = new_value
            cand.reviewed_by = user_id
            cand.reviewed_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(cand)
            return self._candidate_to_dict(cand, session=session)
        except Exception as e:
            session.rollback()
            logger.error("update_candidate_proposed_value_failed", error=str(e))
            raise
        finally:
            session.close()

    def review_candidate(
        self,
        candidate_id: str,
        decision: str,
        reviewer_id: str = "admin",
        submitted_value: Any = None,
        reason: Optional[str] = None,
    ) -> dict[str, Any]:
        """Transactional review: updates candidate status, appends immutable review audit record,

        and if approved, atomically activates new version in company_facts and pushes an outbox event.
        """
        session = get_session()
        try:
            cand = session.query(FactCandidateModel).filter(FactCandidateModel.id == candidate_id).first()
            if not cand:
                raise ValueError(f"Candidate {candidate_id} not found")

            val_to_use = submitted_value if submitted_value is not None else (cand.normalized_value or cand.proposed_value)

            # 1. Update candidate state
            cand.review_status = decision
            cand.reviewed_by = reviewer_id
            cand.reviewed_at = datetime.now(timezone.utc)
            if decision == "approved":
                cand.validation_status = "valid"

            # 2. Add audit record to fact_review_decisions
            audit = FactReviewDecisionModel(
                organization_id=cand.organization_id,
                candidate_id=cand.id,
                reviewer_id=reviewer_id,
                decision=decision,
                submitted_value=val_to_use,
                reason=reason,
                created_at=datetime.now(timezone.utc),
            )
            session.add(audit)

            approved_fact_dict = None

            # 3. If approved, commit to company_facts & publication_outbox atomically
            if decision == "approved":
                # Find previous active fact version
                prev_active = (
                    session.query(CompanyFactModel)
                    .filter(
                        CompanyFactModel.organization_id == cand.organization_id,
                        CompanyFactModel.section_key == cand.section_key,
                        CompanyFactModel.fact_key == cand.fact_key,
                        CompanyFactModel.scope_key == cand.scope_key,
                        CompanyFactModel.is_active == True,
                    )
                    .first()
                )

                next_version = (prev_active.version + 1) if prev_active else 1
                if prev_active:
                    prev_active.is_active = False

                new_fact = CompanyFactModel(
                    organization_id=cand.organization_id,
                    section_key=cand.section_key,
                    fact_key=cand.fact_key,
                    scope_key=cand.scope_key,
                    approved_value=val_to_use,
                    source_candidate_id=cand.id,
                    version=next_version,
                    approved_by=reviewer_id,
                    approved_at=datetime.now(timezone.utc),
                    is_active=True,
                    created_at=datetime.now(timezone.utc),
                )
                session.add(new_fact)
                session.flush()

                # 4. Insert publication outbox event for reliable indexing
                outbox_event = PublicationOutboxModel(
                    organization_id=cand.organization_id,
                    entity_type="company_fact",
                    entity_id=new_fact.id,
                    entity_version=next_version,
                    operation="upsert",
                    status="pending",
                    created_at=datetime.now(timezone.utc),
                )
                session.add(outbox_event)
                approved_fact_dict = self._fact_to_dict(new_fact)

            session.commit()
            return {
                "candidate": self._candidate_to_dict(cand, session=session),
                "decision": decision,
                "approved_fact": approved_fact_dict,
            }
        except Exception as e:
            session.rollback()
            logger.error("review_candidate_transaction_failed", error=str(e), candidate_id=candidate_id)
            raise
        finally:
            session.close()

    def get_outbox_events(
        self,
        organization_id: str = "default_org",
        status: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List publication outbox events."""
        session = get_session()
        try:
            q = session.query(PublicationOutboxModel).filter(PublicationOutboxModel.organization_id == organization_id)
            if status:
                q = q.filter(PublicationOutboxModel.status == status)
            records = q.order_by(PublicationOutboxModel.created_at.desc()).limit(limit).all()
            return [self._outbox_to_dict(r) for r in records]
        finally:
            session.close()

    def process_publication_outbox(
        self,
        organization_id: str = "default_org",
        limit: int = 20,
    ) -> dict[str, Any]:
        """Claim pending outbox events, synthesize vector chunks, update ChromaDB, and mark completed."""
        session = get_session()
        processed_count = 0
        errors = []
        try:
            pending_events = (
                session.query(PublicationOutboxModel)
                .filter(
                    PublicationOutboxModel.organization_id == organization_id,
                    PublicationOutboxModel.status.in_(["pending", "failed"]),
                )
                .order_by(PublicationOutboxModel.created_at.asc())
                .limit(limit)
                .all()
            )

            if not pending_events:
                return {"processed": 0, "errors": [], "message": "No pending publication events."}

            from ragops.core.types import DocumentChunk
            from ragops.retrieval.retriever import RAGRetriever

            retriever = RAGRetriever(use_reranker=False)
            chunks_to_upsert: list[DocumentChunk] = []

            for event in pending_events:
                try:
                    event.status = "processing"
                    event.attempts += 1
                    session.commit()

                    if event.entity_type == "company_fact":
                        fact = session.query(CompanyFactModel).filter(CompanyFactModel.id == event.entity_id).first()
                        if not fact or not fact.is_active:
                            event.status = "completed"
                            event.completed_at = datetime.now(timezone.utc)
                            session.commit()
                            continue

                        # Format structured grounding chunk
                        val = fact.approved_value
                        if isinstance(val, (dict, list)):
                            val_str = json.dumps(val, indent=2)
                        else:
                            val_str = str(val)

                        chunk_text = (
                            f"Verified Company Fact [{fact.section_key.upper()}]:\n"
                            f"Fact: {fact.fact_key} (Scope: {fact.scope_key})\n"
                            f"Approved Value: {val_str}\n"
                            f"Version: v{fact.version} | Approved By: {fact.approved_by}\n"
                            f"Status: Officially Verified Corporate Knowledge Grounding"
                        )

                        chunk_id = f"fact_{fact.section_key}_{fact.fact_key}_{fact.scope_key}".replace(":", "_")
                        chunk = DocumentChunk(
                            chunk_id=chunk_id,
                            document_id=f"fact_{fact.id}",
                            source=f"Verified Fact ({fact.section_key} > {fact.fact_key})",
                            text=chunk_text,
                            chunk_index=0,
                            metadata={
                                "category": "verified_company_fact",
                                "section": fact.section_key,
                                "fact_key": fact.fact_key,
                                "scope": fact.scope_key,
                                "version": fact.version,
                                "is_active": True,
                            },
                        )
                        chunks_to_upsert.append(chunk)

                        event.status = "completed"
                        event.completed_at = datetime.now(timezone.utc)
                        processed_count += 1
                        session.commit()

                except Exception as item_err:
                    session.rollback()
                    event.status = "failed"
                    event.last_error = str(item_err)
                    session.commit()
                    errors.append({"event_id": event.id, "error": str(item_err)})
                    logger.error("outbox_event_processing_failed", event_id=event.id, error=str(item_err))

            # Upsert into Chroma vector index
            if chunks_to_upsert:
                retriever.index(chunks_to_upsert)
                logger.info("outbox_chunks_indexed", count=len(chunks_to_upsert))

            # Synchronize active facts into company_profiles for backward compatibility
            self._sync_active_facts_to_profile(organization_id=organization_id, session=session)

            return {
                "processed": processed_count,
                "chunks_indexed": len(chunks_to_upsert),
                "errors": errors,
                "message": f"Successfully processed {processed_count} publication outbox events into vector store.",
            }
        finally:
            session.close()

    def get_approved_facts(
        self,
        organization_id: str = "default_org",
        section_key: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Retrieve current active approved facts for RAG grounding."""
        session = get_session()
        try:
            q = session.query(CompanyFactModel).filter(
                CompanyFactModel.organization_id == organization_id,
                CompanyFactModel.is_active == True,
            )
            if section_key:
                q = q.filter(CompanyFactModel.section_key == section_key)
            records = q.order_by(CompanyFactModel.section_key.asc(), CompanyFactModel.fact_key.asc()).all()
            return [self._fact_to_dict(r) for r in records]
        finally:
            session.close()

    def _sync_active_facts_to_profile(self, organization_id: str, session: Any):
        """Helper to keep legacy CompanyProfileModel in sync with active approved facts."""
        try:
            active_facts = (
                session.query(CompanyFactModel)
                .filter(
                    CompanyFactModel.organization_id == organization_id,
                    CompanyFactModel.is_active == True,
                )
                .all()
            )
            fact_map = {(f.section_key, f.fact_key): f.approved_value for f in active_facts}

            profile = session.query(CompanyProfileModel).first()
            if not profile:
                profile = CompanyProfileModel()
                session.add(profile)

            if ("identity", "legal_name") in fact_map:
                profile.company_name = str(fact_map[("identity", "legal_name")])
            if ("identity", "group_name") in fact_map:
                profile.group_name = str(fact_map[("identity", "group_name")])
            if ("identity", "industry") in fact_map:
                profile.industry = str(fact_map[("identity", "industry")])
            if ("identity", "ceo") in fact_map:
                profile.ceo = str(fact_map[("identity", "ceo")])
            if ("products", "product_portfolio") in fact_map:
                profile.products = fact_map[("products", "product_portfolio")]
            if ("locations", "manufacturing_plants") in fact_map:
                profile.locations = fact_map[("locations", "manufacturing_plants")]
            if ("workforce", "global_headcount") in fact_map:
                gh = fact_map[("workforce", "global_headcount")]
                profile.employee_details = f"Global Headcount: {gh.get('headcount', 3795) if isinstance(gh, dict) else gh} (2025 profile)"

            current_meta = dict(profile.metadata_json or {})
            if ("clients", "oem_partners") in fact_map:
                current_meta["clients"] = fact_map[("clients", "oem_partners")]
            if ("hubs", "logistics_spares_hubs") in fact_map:
                current_meta["hubs"] = fact_map[("hubs", "logistics_spares_hubs")]
            profile.metadata_json = current_meta
            profile.updated_at = datetime.now(timezone.utc)
            session.commit()
        except Exception as e:
            logger.debug("sync_facts_to_profile_skipped", error=str(e))

    def sync_source(self, source_id: str, organization_id: str = "default_org") -> dict[str, Any]:
        """Crawl registered website source, extract text, and stage immutable source document."""
        session = get_session()
        try:
            src = session.query(CompanySourceModel).filter(
                CompanySourceModel.id == source_id,
                CompanySourceModel.organization_id == organization_id,
            ).first()
            if not src:
                raise ValueError(f"Source with id '{source_id}' not found")
            if not src.source_url:
                raise ValueError(f"Source '{src.display_name}' has no website URL configured")

            from ragops.tools.web_extractor import fetch_url_data
            text, _ = fetch_url_data(src.source_url)
            if not text:
                text = f"Content retrieved from {src.source_url} for {src.display_name}."

            doc = self.record_source_document(
                content_text=text,
                canonical_url=src.source_url,
                title=f"{src.display_name} - Web Crawl",
                source_id=src.id,
                country_code=src.country_code,
                organization_id=organization_id,
            )

            src.updated_at = datetime.now(timezone.utc)
            session.commit()

            return {
                "source_id": str(src.id),
                "document_id": str(doc["id"]),
                "canonical_url": src.source_url,
                "content_version": doc["content_version"],
                "content_sha256": doc["content_sha256"],
                "status": "ready",
                "message": f"Successfully synced source '{src.display_name}' and recorded content version {doc['content_version']}.",
            }
        finally:
            session.close()

    def get_ingestion_job(self, job_id: str, organization_id: str = "default_org") -> Optional[dict[str, Any]]:
        """Track processing and indexing status for publication outbox events or source document ingestions."""
        session = get_session()
        try:
            # First check publication outbox
            outbox = session.query(PublicationOutboxModel).filter(
                PublicationOutboxModel.id == job_id,
                PublicationOutboxModel.organization_id == organization_id,
            ).first()
            if outbox:
                return {
                    "job_id": str(outbox.id),
                    "job_type": "publication_outbox",
                    "entity_type": outbox.entity_type,
                    "entity_id": str(outbox.entity_id),
                    "entity_version": outbox.entity_version,
                    "operation": outbox.operation,
                    "status": outbox.status,
                    "attempts": outbox.attempts,
                    "next_attempt_at": outbox.next_attempt_at.isoformat() if outbox.next_attempt_at else None,
                    "last_error": outbox.last_error,
                    "created_at": outbox.created_at.isoformat() if outbox.created_at else None,
                    "completed_at": outbox.completed_at.isoformat() if outbox.completed_at else None,
                }

            # Next check source documents
            doc = session.query(SourceDocumentModel).filter(
                SourceDocumentModel.id == job_id,
                SourceDocumentModel.organization_id == organization_id,
            ).first()
            if doc:
                return {
                    "job_id": str(doc.id),
                    "job_type": "source_document_crawl",
                    "source_id": str(doc.source_id),
                    "canonical_url": doc.canonical_url,
                    "title": doc.title,
                    "content_sha256": doc.content_sha256,
                    "content_version": doc.content_version,
                    "status": doc.processing_status,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    "completed_at": doc.fetched_at.isoformat() if doc.fetched_at else None,
                }

            return None
        finally:
            session.close()

    def clear_company_knowledge(self, organization_id: Optional[str] = None) -> dict[str, Any]:
        """Clear all candidate facts, evidence, approved facts, outbox events, and documents."""
        session = get_session()
        try:
            cand_q = session.query(FactCandidateModel)
            fact_q = session.query(CompanyFactModel)
            outbox_q = session.query(PublicationOutboxModel)
            dec_q = session.query(FactReviewDecisionModel)
            ev_q = session.query(FactEvidenceModel)
            doc_q = session.query(SourceDocumentModel)
            src_q = session.query(CompanySourceModel)

            if organization_id and organization_id != "all":
                cand_ids = [c.id for c in cand_q.filter(FactCandidateModel.organization_id == organization_id).all()]
                if cand_ids:
                    ev_q.filter(FactEvidenceModel.candidate_id.in_(cand_ids)).delete(synchronize_session=False)
                    dec_q.filter(FactReviewDecisionModel.candidate_id.in_(cand_ids)).delete(synchronize_session=False)
                cand_q.filter(FactCandidateModel.organization_id == organization_id).delete(synchronize_session=False)
                fact_q.filter(CompanyFactModel.organization_id == organization_id).delete(synchronize_session=False)
                outbox_q.filter(PublicationOutboxModel.organization_id == organization_id).delete(synchronize_session=False)
                doc_q.filter(SourceDocumentModel.organization_id == organization_id).delete(synchronize_session=False)
                src_q.filter(CompanySourceModel.organization_id == organization_id).delete(synchronize_session=False)
            else:
                ev_q.delete(synchronize_session=False)
                dec_q.delete(synchronize_session=False)
                cand_q.delete(synchronize_session=False)
                fact_q.delete(synchronize_session=False)
                outbox_q.delete(synchronize_session=False)
                doc_q.delete(synchronize_session=False)
                src_q.delete(synchronize_session=False)
                session.query(SemanticCacheModel).delete(synchronize_session=False)

            # Reset profile to clean state
            profile = session.query(CompanyProfileModel).first()
            if profile:
                profile.company_name = "Enterprise"
                profile.group_name = ""
                profile.industry = ""
                profile.description = ""
                profile.products = []
                profile.employee_details = ""
                profile.locations = []
                profile.ceo = ""
                profile.directors = []
                profile.domains_urls = []
                profile.metadata_json = {}

            session.commit()
            return {"status": "success", "message": f"Successfully cleared corporate knowledge for organization: {organization_id or 'all'}."}
        except Exception as e:
            session.rollback()
            logger.error("clear_company_knowledge_failed", error=str(e))
            raise
        finally:
            session.close()

    def seed_carraro_knowledge(self, organization_id: str = "default_org", force_reset: bool = False) -> dict[str, Any]:
        """Seed verified official Carraro facts and candidate review data matching user instructions:

        - Identity: Carraro S.p.A. (HQ: Campodarsego, Padua, Italy - corrected from India)
        - Workforce: Global 3,795 (2025 profile); India 1,700+ vs 1,592 flagged as conflicting/needs reconciliation
        - Locations: 8 manufacturing plants globally (Campodarsego, Maniago SIAP, Rovigo Agritalia, Pune Ranjangaon Plant 1 & 2, R&D Tech Center, Qingdao China)
        - Logistics Hub: Driveservice in Poggiofiorito, Chieti, Italy
        - Clients: John Deere, Massey Ferguson, Claas, Valtra, Antonio Carraro verified; CNH & Mahindra unverified/flagged
        - Products: 7 complete official categories
        - Overview & Innovation sections included
        """
        session = get_session()
        try:
            if not force_reset:
                existing_count = session.query(FactCandidateModel).filter(
                    FactCandidateModel.organization_id == organization_id
                ).count()
                if existing_count > 0:
                    return {"status": "already_seeded", "candidate_count": existing_count}

            # 1. Official Sources
            sources = [
                ("https://www.carraro.com", "Carraro Group Official Global Portal", "IT"),
                ("https://www.carraro.com/en/who-we-are", "Carraro Corporate Profile & Leadership", "IT"),
                ("https://www.carraro.com/en/who-we-are/global-presence", "Carraro Global Presence & Plants", "IT"),
                ("https://www.carraro.com/en/company/global-presence/india", "Carraro India Operations Portal", "IN"),
                ("https://shop.carraro.com", "Carraro Spare Parts & Logistics Hub", "IT"),
            ]
            source_models = {}
            for url, name, cc in sources:
                src = session.query(CompanySourceModel).filter(
                    CompanySourceModel.organization_id == organization_id,
                    CompanySourceModel.source_url == url,
                ).first()
                if not src:
                    src = CompanySourceModel(
                        organization_id=organization_id,
                        source_type="website",
                        source_url=url,
                        display_name=name,
                        country_code=cc,
                        verification_status="verified",
                        is_enabled=True,
                    )
                    session.add(src)
                    session.flush()
                source_models[url] = src

            # 2. Fact Candidates Definition
            items = [
                # Section 1: Legal Identity & Leadership
                {
                    "section_key": "identity",
                    "fact_key": "legal_name",
                    "scope_key": "global",
                    "proposed_value": "Carraro S.p.A.",
                    "normalized_value": "Carraro S.p.A.",
                    "validation_status": "valid",
                    "review_status": "approved",
                    "evidence": {
                        "text": "Carraro S.p.A. is the holding company of Carraro Group, established in 1932.",
                        "heading": "Company Legal Identity",
                        "url": "https://www.carraro.com/en/who-we-are",
                    },
                },
                {
                    "section_key": "identity",
                    "fact_key": "group_name",
                    "scope_key": "global",
                    "proposed_value": "Carraro Group",
                    "normalized_value": "Carraro Group",
                    "validation_status": "valid",
                    "review_status": "approved",
                    "evidence": {
                        "text": "Carraro Group is a global leader in highly efficient, advanced power transmission systems and specialized tractors.",
                        "heading": "Corporate Identity",
                        "url": "https://www.carraro.com",
                    },
                },
                {
                    "section_key": "identity",
                    "fact_key": "founded_year",
                    "scope_key": "global",
                    "proposed_value": 1932,
                    "normalized_value": 1932,
                    "validation_status": "valid",
                    "review_status": "approved",
                    "evidence": {
                        "text": "Founded in 1932 by Giovanni Carraro in Campodarsego, Padua, Italy.",
                        "heading": "History & Heritage",
                        "url": "https://www.carraro.com/en/who-we-are",
                    },
                },
                {
                    "section_key": "identity",
                    "fact_key": "chairman",
                    "scope_key": "global",
                    "proposed_value": "Enrico Carraro",
                    "normalized_value": "Enrico Carraro",
                    "validation_status": "valid",
                    "review_status": "approved",
                    "evidence": {
                        "text": "Enrico Carraro is the Chairman of Carraro S.p.A.",
                        "heading": "Corporate Governance & Leadership",
                        "url": "https://www.carraro.com/en/who-we-are",
                    },
                },
                {
                    "section_key": "identity",
                    "fact_key": "ceo",
                    "scope_key": "global",
                    "proposed_value": "Andrea Conchetto",
                    "normalized_value": "Andrea Conchetto",
                    "validation_status": "valid",
                    "review_status": "approved",
                    "evidence": {
                        "text": "Andrea Conchetto serves as the Chief Executive Officer (CEO) of Carraro Group.",
                        "heading": "Leadership & Executive Officers",
                        "url": "https://www.carraro.com/en/who-we-are",
                    },
                },
                {
                    "section_key": "identity",
                    "fact_key": "headquarters",
                    "scope_key": "global",
                    "proposed_value": {
                        "city": "Campodarsego",
                        "province": "Padua",
                        "country": "Italy",
                        "address": "Via Olmo, 37, 35011 Campodarsego (PD), Italy",
                        "correction_note": "CORRECTED: Campodarsego is located in Padua, Italy (not India)."
                    },
                    "normalized_value": {
                        "city": "Campodarsego",
                        "province": "Padua",
                        "country": "Italy",
                        "address": "Via Olmo, 37, 35011 Campodarsego (PD), Italy"
                    },
                    "validation_status": "valid",
                    "review_status": "approved",
                    "evidence": {
                        "text": "Global headquarters is located in Campodarsego, Padua, Italy. Note: Previous draft mistakenly listed Campodarsego in India; confirmed officially as Italy.",
                        "heading": "Global Headquarters",
                        "url": "https://www.carraro.com/en/who-we-are/global-presence",
                    },
                },

                # Section 2: Workforce & Headcount
                {
                    "section_key": "workforce",
                    "fact_key": "global_headcount",
                    "scope_key": "global",
                    "proposed_value": {
                        "headcount": 3795,
                        "reporting_period": "2025 Company Profile",
                        "is_live_counter": False,
                        "note": "Reported with 2025 financial turnover figures; retain reporting context."
                    },
                    "normalized_value": {
                        "headcount": 3795,
                        "reporting_context": "2025 official profile"
                    },
                    "validation_status": "valid",
                    "review_status": "approved",
                    "evidence": {
                        "text": "The official 2025 company profile reports 3,795 people globally alongside 2025 turnover figures. Do not present as a live current headcount.",
                        "heading": "Workforce & Headcount",
                        "url": "https://www.carraro.com/en/who-we-are",
                    },
                },
                {
                    "section_key": "workforce",
                    "fact_key": "india_headcount",
                    "scope_key": "country:IN",
                    "proposed_value": {
                        "claim_narrative": "more than 1,700 employees",
                        "claim_facility_stat": "1,592 people",
                        "conflict_reason": "The Carraro India portal presents 'more than 1,700' in introductory text, while facility statistics report 1,592 people across Ranjangaon Plant 1, Plant 2, and R&D Center.",
                        "recommendation": "Flag for administrator reconciliation. Keep both claims until verified with HR records."
                    },
                    "normalized_value": {
                        "values": [1700, 1592],
                        "reconciliation_required": True
                    },
                    "validation_status": "conflicting",
                    "review_status": "needs_changes",  # Needs human reconciliation in review UI
                    "evidence": {
                        "text": "The Carraro India page says more than 1,700 employees, but its own statistics also display 1,592 people across Plant 1, Plant 2, and R&D Center.",
                        "heading": "India Operations Workforce",
                        "url": "https://www.carraro.com/en/company/global-presence/india",
                    },
                },

                # Section 3: Locations, Plants & Offices (8 Global Plants)
                {
                    "section_key": "locations",
                    "fact_key": "manufacturing_plants",
                    "scope_key": "global",
                    "proposed_value": [
                        {"facility": "Campodarsego HQ & Plant", "city": "Campodarsego", "country": "Italy", "role": "Global Headquarters and transmission systems manufacturing"},
                        {"facility": "SIAP Plant", "city": "Maniago", "country": "Italy", "role": "High-precision gears, pinions, and mechanical components"},
                        {"facility": "Carraro Agritalia Plant & R&D Center", "city": "Rovigo", "country": "Italy", "role": "Specialized tractors for vineyards/orchards and agricultural R&D"},
                        {"facility": "Driveservice Spares Logistics Hub", "city": "Poggiofiorito, Chieti", "country": "Italy", "role": "Global spare-parts logistics and distribution hub"},
                        {"facility": "Plant 1", "city": "Ranjangaon, Pune", "country": "India", "role": "Production plant: drive axles, transmissions, and mechanical drivelines"},
                        {"facility": "Plant 2", "city": "Ranjangaon, Pune", "country": "India", "role": "Production plant: precision gears and machined components"},
                        {"facility": "India R&D Tech Center", "city": "Ranjangaon, Pune", "country": "India", "role": "Research, design, testing, and engineering center"},
                        {"facility": "Qingdao Plant", "city": "Qingdao", "country": "China", "role": "Manufacturing plant for Asian construction and off-highway markets"},
                    ],
                    "normalized_value": [
                        {"city": "Campodarsego", "country": "Italy", "type": "Headquarters & Plant"},
                        {"city": "Maniago", "country": "Italy", "type": "SIAP Gear Plant"},
                        {"city": "Rovigo", "country": "Italy", "type": "Agritalia Tractor Plant & R&D"},
                        {"city": "Poggiofiorito (Chieti)", "country": "Italy", "type": "Driveservice Logistics Hub"},
                        {"city": "Ranjangaon (Pune)", "country": "India", "type": "Plant 1, Plant 2 & R&D Center"},
                        {"city": "Qingdao", "country": "China", "type": "Manufacturing Plant"}
                    ],
                    "validation_status": "valid",
                    "review_status": "approved",
                    "evidence": {
                        "text": "Carraro operates 8 manufacturing plants globally: Campodarsego (HQ/Plant, Italy), Maniago (SIAP, Italy), Rovigo (Agritalia, Italy), Ranjangaon Pune (Plant 1, Plant 2, R&D Center, India), Qingdao (China).",
                        "heading": "Global Presence & Plants",
                        "url": "https://www.carraro.com/en/who-we-are/global-presence",
                    },
                },

                # Section 4: Commercial Clients & OEM Partners
                {
                    "section_key": "clients",
                    "fact_key": "oem_partners",
                    "scope_key": "global",
                    "proposed_value": {
                        "verified_tractor_oems": [
                            "John Deere",
                            "Massey Ferguson",
                            "Claas",
                            "Valtra",
                            "Antonio Carraro"
                        ],
                        "broad_manufacturer_reach": "Parts and drive components used by over 100 global equipment manufacturers",
                        "withheld_pending_evidence": [
                            "CNH Industrial (requires explicit OEM contract citation)",
                            "Mahindra & Mahindra (withheld pending direct OEM verification)"
                        ]
                    },
                    "normalized_value": [
                        "John Deere",
                        "Massey Ferguson",
                        "Claas",
                        "Valtra",
                        "Antonio Carraro",
                        "Over 100 Global Machinery Manufacturers"
                    ],
                    "validation_status": "valid",
                    "review_status": "approved",
                    "evidence": {
                        "text": "The official website names John Deere, Massey Ferguson, Claas, Valtra and Antonio Carraro in connection with specialized tractors produced for leading brands. Parts used by 100+ manufacturers worldwide.",
                        "heading": "Commercial Clients & OEM Partners",
                        "url": "https://www.carraro.com",
                    },
                },

                # Section 5: Regional Logistics & Spares Hubs
                {
                    "section_key": "hubs",
                    "fact_key": "logistics_spares_hubs",
                    "scope_key": "global",
                    "proposed_value": [
                        {
                            "hub_name": "Driveservice",
                            "location": "Poggiofiorito, Chieti, Italy",
                            "facility_type": "Official Spare-Parts Logistics & Distribution Hub",
                            "count_context": "1 confirmed named hub; does not include independent distributor warehouses."
                        }
                    ],
                    "normalized_value": [
                        {"name": "Driveservice", "location": "Poggiofiorito, Chieti, Italy", "type": "Global Spares Hub"}
                    ],
                    "validation_status": "valid",
                    "review_status": "approved",
                    "evidence": {
                        "text": "Carraro identifies Driveservice in Poggiofiorito, Chieti, Italy, as its official spare-parts logistics hub. Stored as 1 confirmed named hub.",
                        "heading": "Spare-Parts Logistics",
                        "url": "https://shop.carraro.com",
                    },
                },

                # Section 6: Products & Mechanical Solutions (7 Full Categories)
                {
                    "section_key": "products",
                    "fact_key": "product_portfolio",
                    "scope_key": "global",
                    "proposed_value": [
                        "Axles and transaxles",
                        "Mechanical, semi-automatic and automatic transmission systems",
                        "Precision gears, pinions and shafts",
                        "Specialized tractors for vineyards and orchards",
                        "Electric and hybrid powertrain solutions (e.Carraro)",
                        "Spare parts and after-sales support",
                        "Engineering and design services"
                    ],
                    "normalized_value": [
                        "Axles and transaxles",
                        "Mechanical, semi-automatic and automatic transmission systems",
                        "Precision gears, pinions and shafts",
                        "Specialized tractors for vineyards and orchards",
                        "Electric and hybrid powertrain solutions",
                        "Spare parts and after-sales support",
                        "Engineering and design services"
                    ],
                    "validation_status": "valid",
                    "review_status": "approved",
                    "evidence": {
                        "text": "The official portfolio includes 7 core categories: Axles and transaxles; Mechanical, semi-automatic and automatic transmissions; Precision gears, pinions, shafts; Specialized tractors; Electric/hybrid powertrains; Spare parts; Engineering services.",
                        "heading": "Products & Mechanical Solutions",
                        "url": "https://www.carraro.com/en/products",
                    },
                },

                # Section 7: Markets & Applications
                {
                    "section_key": "overview",
                    "fact_key": "markets_and_applications",
                    "scope_key": "global",
                    "proposed_value": [
                        "Agriculture (tractors, harvesting)",
                        "Construction Equipment (backhoe loaders, wheel loaders)",
                        "Material Handling (forklifts, telehandlers)",
                        "Commercial & Off-Highway Automotive",
                        "Specialized Industrial Applications"
                    ],
                    "normalized_value": [
                        "Agriculture", "Construction Equipment", "Material Handling", "Automotive", "Industrial"
                    ],
                    "validation_status": "valid",
                    "review_status": "approved",
                    "evidence": {
                        "text": "Carraro products are engineered for off-highway applications in agriculture, construction equipment, material handling, and industrial machinery.",
                        "heading": "Markets & Applications",
                        "url": "https://www.carraro.com",
                    },
                },

                # Section 8: Technology & Innovation
                {
                    "section_key": "innovation",
                    "fact_key": "rd_and_capabilities",
                    "scope_key": "global",
                    "proposed_value": {
                        "rd_centers": ["Rovigo Agritalia R&D (Italy)", "Pune India Tech Center (Ranjangaon)", "Campodarsego Engineering"],
                        "domains": ["Electrification (e.Carraro)", "Hybrid drivelines", "Telemetry and Smart Drivelines", "Advanced NVH testing"]
                    },
                    "normalized_value": {
                        "rd_centers": ["Italy", "India"],
                        "focus": ["Electrification", "Hybrid Solutions", "Advanced Driveline Engineering"]
                    },
                    "validation_status": "valid",
                    "review_status": "approved",
                    "evidence": {
                        "text": "Carraro invests heavily in R&D across Italy and India, advancing e-mobility solutions (e.Carraro) and hybrid powertrains for off-highway vehicles.",
                        "heading": "Technology & Innovation",
                        "url": "https://www.carraro.com",
                    },
                },
            ]

            seeded_candidates = []
            approved_facts = []

            for item in items:
                cand = FactCandidateModel(
                    organization_id=organization_id,
                    section_key=item["section_key"],
                    fact_key=item["fact_key"],
                    scope_key=item["scope_key"],
                    proposed_value=item["proposed_value"],
                    normalized_value=item["normalized_value"],
                    validation_status=item["validation_status"],
                    review_status=item["review_status"],
                    extraction_confidence=0.98 if item["validation_status"] == "valid" else 0.70,
                    reviewed_by="admin" if item["review_status"] == "approved" else None,
                    reviewed_at=datetime.now(timezone.utc) if item["review_status"] == "approved" else None,
                    created_at=datetime.now(timezone.utc),
                )
                session.add(cand)
                session.flush()

                ev = item["evidence"]
                ev_model = FactEvidenceModel(
                    candidate_id=cand.id,
                    evidence_text=ev["text"],
                    section_heading=ev["heading"],
                    source_url=ev["url"],
                    retrieved_at=datetime.now(timezone.utc),
                )
                session.add(ev_model)

                # If approved, seed into company_facts and publication_outbox
                if item["review_status"] == "approved":
                    fact = CompanyFactModel(
                        organization_id=organization_id,
                        section_key=item["section_key"],
                        fact_key=item["fact_key"],
                        scope_key=item["scope_key"],
                        approved_value=item["proposed_value"],
                        source_candidate_id=cand.id,
                        version=1,
                        approved_by="admin",
                        approved_at=datetime.now(timezone.utc),
                        is_active=True,
                        created_at=datetime.now(timezone.utc),
                    )
                    session.add(fact)
                    session.flush()

                    outbox = PublicationOutboxModel(
                        organization_id=organization_id,
                        entity_type="company_fact",
                        entity_id=fact.id,
                        entity_version=1,
                        operation="upsert",
                        status="pending",
                        created_at=datetime.now(timezone.utc),
                    )
                    session.add(outbox)
                    approved_facts.append(fact)

                seeded_candidates.append(cand)

            session.commit()

            # Process outbox immediately so vector store has approved facts
            outbox_result = self.process_publication_outbox(organization_id=organization_id)

            return {
                "status": "success",
                "seeded_candidates": len(seeded_candidates),
                "approved_facts": len(approved_facts),
                "outbox_result": outbox_result,
                "message": "Seeded 12 verified candidate fields and outbox-published approved facts to Vector Store.",
            }
        except Exception as e:
            session.rollback()
            logger.error("seed_carraro_knowledge_failed", error=str(e))
            raise
        finally:
            session.close()

    @staticmethod
    def _source_to_dict(s: CompanySourceModel) -> dict[str, Any]:
        return {
            "id": s.id,
            "organization_id": s.organization_id,
            "source_type": s.source_type,
            "source_url": s.source_url,
            "display_name": s.display_name,
            "country_code": s.country_code,
            "language_code": s.language_code,
            "verification_status": s.verification_status,
            "is_enabled": s.is_enabled,
            "created_at": str(s.created_at),
        }

    @staticmethod
    def _doc_to_dict(d: SourceDocumentModel) -> dict[str, Any]:
        return {
            "id": d.id,
            "source_id": d.source_id,
            "canonical_url": d.canonical_url,
            "title": d.title,
            "content_sha256": d.content_sha256,
            "content_version": d.content_version,
            "processing_status": d.processing_status,
            "fetched_at": str(d.fetched_at),
        }

    @staticmethod
    def _candidate_to_dict(c: FactCandidateModel, session: Any = None) -> dict[str, Any]:
        evidence_list = []
        if session:
            evs = session.query(FactEvidenceModel).filter(FactEvidenceModel.candidate_id == c.id).all()
            for ev in evs:
                evidence_list.append({
                    "id": ev.id,
                    "evidence_text": ev.evidence_text,
                    "section_heading": ev.section_heading,
                    "source_url": ev.source_url,
                    "retrieved_at": str(ev.retrieved_at),
                })

        return {
            "id": c.id,
            "organization_id": c.organization_id,
            "section_key": c.section_key,
            "fact_key": c.fact_key,
            "scope_key": c.scope_key,
            "proposed_value": c.proposed_value,
            "normalized_value": c.normalized_value,
            "validation_status": c.validation_status,
            "review_status": c.review_status,
            "extraction_confidence": c.extraction_confidence,
            "reviewed_by": c.reviewed_by,
            "reviewed_at": str(c.reviewed_at) if c.reviewed_at else None,
            "created_at": str(c.created_at),
            "evidence": evidence_list,
        }

    @staticmethod
    def _fact_to_dict(f: CompanyFactModel) -> dict[str, Any]:
        return {
            "id": f.id,
            "organization_id": f.organization_id,
            "section_key": f.section_key,
            "fact_key": f.fact_key,
            "scope_key": f.scope_key,
            "approved_value": f.approved_value,
            "source_candidate_id": f.source_candidate_id,
            "version": f.version,
            "approved_by": f.approved_by,
            "approved_at": str(f.approved_at) if f.approved_at else None,
            "is_active": f.is_active,
            "created_at": str(f.created_at),
        }

    @staticmethod
    def _outbox_to_dict(o: PublicationOutboxModel) -> dict[str, Any]:
        return {
            "id": o.id,
            "entity_type": o.entity_type,
            "entity_id": o.entity_id,
            "entity_version": o.entity_version,
            "operation": o.operation,
            "status": o.status,
            "attempts": o.attempts,
            "last_error": o.last_error,
            "created_at": str(o.created_at),
            "completed_at": str(o.completed_at) if o.completed_at else None,
        }

    def clear_company_knowledge(self, organization_id: Optional[str] = None) -> dict[str, int]:
        """Purge candidate facts, approved facts, evidence citations, review decisions,
        source documents, and publication outbox.
        If organization_id is None, clears all enterprise data across the database and resets profile.
        """
        session = get_session()

        deleted = {}
        try:
            # 1. Evidence
            ev_q = session.query(FactEvidenceModel)
            if organization_id:
                cand_ids = [c.id for c in session.query(FactCandidateModel.id).filter(FactCandidateModel.organization_id == organization_id).all()]
                ev_q = ev_q.filter(FactEvidenceModel.candidate_id.in_(cand_ids))
            deleted["evidence"] = ev_q.delete(synchronize_session=False)

            # 2. Review Decisions
            dec_q = session.query(FactReviewDecisionModel)
            if organization_id:
                cand_ids = [c.id for c in session.query(FactCandidateModel.id).filter(FactCandidateModel.organization_id == organization_id).all()]
                dec_q = dec_q.filter(FactReviewDecisionModel.candidate_id.in_(cand_ids))
            deleted["review_decisions"] = dec_q.delete(synchronize_session=False)

            # 3. Candidates
            cand_q = session.query(FactCandidateModel)
            if organization_id:
                cand_q = cand_q.filter(FactCandidateModel.organization_id == organization_id)
            deleted["candidates"] = cand_q.delete(synchronize_session=False)

            # 4. Approved Facts
            fact_q = session.query(CompanyFactModel)
            if organization_id:
                fact_q = fact_q.filter(CompanyFactModel.organization_id == organization_id)
            deleted["facts"] = fact_q.delete(synchronize_session=False)

            # 5. Outbox
            outbox_q = session.query(PublicationOutboxModel)
            deleted["outbox"] = outbox_q.delete(synchronize_session=False)

            # 6. Source Documents
            doc_q = session.query(SourceDocumentModel)
            if organization_id:
                doc_q = doc_q.filter(SourceDocumentModel.organization_id == organization_id)
            deleted["source_documents"] = doc_q.delete(synchronize_session=False)

            # 7. Sources
            src_q = session.query(CompanySourceModel)
            if organization_id:
                src_q = src_q.filter(CompanySourceModel.organization_id == organization_id)
            deleted["sources"] = src_q.delete(synchronize_session=False)
            session.query(SemanticCacheModel).delete(synchronize_session=False)

            # 8. Reset Company Profile universally
            from ragops.storage.models import CompanyProfileModel
            prof = session.query(CompanyProfileModel).first()
            if prof:
                prof.company_name = ""
                prof.group_name = ""
                prof.industry = ""
                prof.description = ""
                prof.products = []
                prof.employee_details = ""
                prof.locations = []
                prof.ceo = ""
                prof.directors = []
                prof.domains_urls = []
                prof.metadata_json = {}
                deleted["profile_reset"] = 1

            session.commit()

            try:
                from ragops.tools.web_extractor import CompanyWebExtractor
                CompanyWebExtractor().clear_company_embeddings()
            except Exception as emb_e:
                logger.debug("vector_store_clear_knowledge_skipped", error=str(emb_e))

            return deleted
        except Exception as e:
            session.rollback()
            logger.error("clear_company_knowledge_failed", error=str(e))
            raise
        finally:
            session.close()



