"""Repositories — data access layer encapsulating SQL queries for users, chat telemetry, and audit logs."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import cast, desc, func, Integer

from ragops.core.auth import UserProfile, verify_password
from ragops.core.logging import get_logger
from ragops.storage.database import get_session
from ragops.storage.models import ChatMessageModel, DocumentModel, FeedbackModel, TraceModel, UserModel

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

    def get_session_messages(self, session_id: str) -> list[dict[str, Any]]:
        """Get all messages in a conversation session in chronological order (turn-by-turn)."""
        session = get_session()
        try:
            records = (
                session.query(ChatMessageModel)
                .filter(ChatMessageModel.session_id == session_id)
                .order_by(ChatMessageModel.created_at.asc())
                .all()
            )
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
    """Repository for querying auto-classified document inventory and statistics."""

    def list_documents(self, doc_type: str | None = None) -> list[dict[str, Any]]:
        """List all indexed documents with classification metadata."""
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
                    "chunk_count": d.chunk_count,
                    "created_at": str(d.created_at),
                }
                for d in docs
            ]
        finally:
            session.close()

    def get_summary(self) -> dict[str, Any]:
        """Get high-level count of documents broken down by classification."""
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

            return {
                "total_documents": total,
                "policies": policies,
                "codes": codes,
                "programmes": programmes,
                "governance": governance,
                "manuals": manuals,
                "others": max(0, others),
            }
        finally:
            session.close()


# -----------------------------------------------------------------------------
# Semantic Cache Repository
# -----------------------------------------------------------------------------

class SemanticCacheRepository:
    """Repository for inspecting and managing the semantic answer cache."""

    def get_cache_stats(self) -> dict[str, Any]:
        """Get aggregate metrics for semantic caching."""
        session = get_session()
        try:
            from ragops.storage.models import SemanticCacheModel
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

            return {
                "total_cached_patterns": total_entries,
                "total_cache_hits": int(total_hits),
                "chat_cache_hits": int(chat_cache_hits),
                "chat_total_queries": int(chat_total),
                "cache_hit_rate_pct": hit_rate_pct,
                "total_latency_saved_ms": round(float(total_saved_ms), 1),
                "total_cost_saved_usd": round(int(chat_cache_hits) * 0.0003, 5),
            }
        finally:
            session.close()

    def list_entries(self, limit: int = 50) -> list[dict[str, Any]]:
        """List active cache entries with hit counts and scopes."""
        session = get_session()
        try:
            from ragops.storage.models import SemanticCacheModel
            entries = (
                session.query(SemanticCacheModel)
                .order_by(SemanticCacheModel.hit_count.desc(), SemanticCacheModel.last_hit_at.desc())
                .limit(limit)
                .all()
            )
            return [
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
                }
                for e in entries
            ]
        finally:
            session.close()

    def clear_cache(self) -> int:
        """Clear all semantic cache entries."""
        session = get_session()
        try:
            from ragops.storage.models import SemanticCacheModel
            count = session.query(SemanticCacheModel).delete()
            session.commit()
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
        """Remove a domain/URL from the profile."""
        session = get_session()
        try:
            from ragops.storage.models import CompanyProfileModel
            profile = session.query(CompanyProfileModel).first()
            if profile and profile.domains_urls:
                urls = [u for u in profile.domains_urls if u.strip() != url.strip()]
                profile.domains_urls = urls
                profile.updated_at = datetime.now(timezone.utc)
                session.commit()
                session.refresh(profile)
            return self._to_dict(profile) if profile else {}
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

