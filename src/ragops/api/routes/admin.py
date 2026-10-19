"""Admin & Observability API routes — user management, chat history inspection, and ML training export."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ragops.storage.database import get_active_db_type
from ragops.storage.repositories import ChatRepository, UserRepository
from ragops.api.dependencies import get_retriever

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
async def list_users():
    """List all registered users along with cumulative token consumption, query counts, and activity."""
    try:
        repo = UserRepository()
        users = repo.list_all_users_with_stats()
        return {"users": users, "total_users": len(users)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {str(e)}")


@router.get("/users/{username}/history")
async def get_user_chat_history(username: str, limit: int = Query(50, ge=1, le=200)):
    """Retrieve complete conversational audit trail and telemetry for a specific user.

    Includes full chunk provenance (scores, pages, doc names) and per-hop latencies.
    """
    try:
        chat_repo = ChatRepository()
        history = chat_repo.get_user_history(username=username, limit=limit)
        return {
            "username": username,
            "total_messages": len(history),
            "history": history,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch user history: {str(e)}")


@router.get("/sessions")
async def list_admin_sessions(
    limit: int = Query(50, ge=1, le=200),
    user: Optional[str] = Query(None, description="Filter by username"),
):
    """Admin view: List all multi-prompt conversation sessions across all users."""
    try:
        chat_repo = ChatRepository()
        sessions = chat_repo.get_all_sessions(limit=limit, user_filter=user)
        return {"count": len(sessions), "sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch sessions: {str(e)}")


@router.get("/sessions/{session_id}")
async def get_admin_session_detail(session_id: str):
    """Admin view: Inspect complete turn-by-turn conversation transcript for a session."""
    try:
        chat_repo = ChatRepository()
        messages = chat_repo.get_session_messages(session_id=session_id)
        return {
            "session_id": session_id,
            "total_turns": len(messages),
            "messages": messages,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch session detail: {str(e)}")


@router.get("/logs")
async def get_all_query_logs(
    limit: int = Query(100, ge=1, le=500),
    user: Optional[str] = Query(None, description="Filter by username"),
    risk_only: bool = Query(False, description="Filter only queries flagged for churn or policy/POSH risk"),
):
    """Admin inspection log: view queries across all users with full telemetry."""
    try:
        chat_repo = ChatRepository()
        logs = chat_repo.get_all_logs(limit=limit, user_filter=user, risk_only=risk_only)
        return {
            "count": len(logs),
            "logs": logs,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch logs: {str(e)}")


@router.get("/analytics")
async def get_admin_analytics():
    """Aggregated observability summary: total tokens, costs, average latency, and risk counts."""
    try:
        chat_repo = ChatRepository()
        summary = chat_repo.get_analytics_summary()
        frequent = chat_repo.get_frequent_queries(limit=6)
        active_db = get_active_db_type()

        try:
            retriever = get_retriever()
            doc_count = retriever.document_count
        except Exception:
            doc_count = 0

        return {
            **summary,
            "frequent_queries": frequent,
            "documents_indexed": doc_count,
            "database_engine": active_db,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch analytics: {str(e)}")


@router.get("/frequent-queries")
async def get_frequent_queries(limit: int = Query(10, ge=1, le=50)):
    """Identify top asked questions to inform FAQ generation and content gap analysis."""
    try:
        chat_repo = ChatRepository()
        queries = chat_repo.get_frequent_queries(limit=limit)
        return {"frequent_queries": queries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch frequent queries: {str(e)}")


@router.get("/training-export")
async def export_training_dataset(limit: int = Query(100, ge=1, le=1000)):
    """Export positive grounded Q&A pairs with context for Model Fine-Tuning (SFT / DPO)."""
    try:
        chat_repo = ChatRepository()
        samples = chat_repo.get_training_samples(limit=limit)
        return {
            "format": "supervised_fine_tuning",
            "sample_count": len(samples),
            "samples": samples,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export training data: {str(e)}")
