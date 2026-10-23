"""Query routes — RAG query and document management endpoints."""

from __future__ import annotations


from pathlib import Path
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from ragops.api.dependencies import get_rag_pipeline, get_retriever
from ragops.core.exceptions import GenerationError, RetrievalError
from ragops.core.types import QueryRequest, RAGResponse
from ragops.ingestion.pipeline import IngestionPipeline
from ragops.ingestion.schemas import IngestionRequest, IngestionResult

from typing import Optional
import time
import uuid
from ragops.storage.repositories import ChatRepository, UserRepository
from ragops.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["query"])


# --- Request/Response Models ---

class QueryInput(BaseModel):
    """API-level query input."""
    query: str
    top_k: int = Field(default=5, ge=1, le=50)
    filters: dict = Field(default_factory=dict)
    username: Optional[str] = Field(default="test1", description="Active authenticated user")
    session_id: Optional[str] = Field(default=None, description="Optional conversational session ID")


class IngestInput(BaseModel):
    """API-level ingestion input."""
    path: str
    document_version: str = "v1"
    metadata: dict = Field(default_factory=dict)


# --- Query Endpoints ---

@router.post("/query", response_model=RAGResponse)
async def query_rag(input: QueryInput):
    """Query the RAG pipeline and get an answer with citations.

    This is the main endpoint for the RAG system.
    Automatically persists full telemetry and chunk provenance to PostgreSQL.
    """
    pipeline = get_rag_pipeline()

    session_id = input.session_id
    if not session_id or session_id.strip() == "" or session_id in ("sess_admin", "sess_test1", "sess_test2", "sess_user", "sess_anon"):
        session_id = f"sess_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"

    request = QueryRequest(
        query=input.query,
        top_k=input.top_k,
        filters=input.filters,
        session_id=session_id,
    )

    try:
        response = pipeline.query(request)

        # Asynchronously or safely persist to PostgreSQL
        try:
            chat_repo = ChatRepository()
            user_repo = UserRepository()
            user_obj = user_repo.get_by_username(input.username or "test1")

            meta = response.metadata or {}
            citations_list = [s.model_dump() if hasattr(s, "model_dump") else dict(s) for s in response.sources]
            chunks_list = meta.get("retrieved_chunks", [])

            chat_repo.save_chat_turn(
                username=input.username or "test1",
                user_id=user_obj.id if user_obj else None,
                query=input.query,
                answer=response.answer,
                trace_id=response.trace_id,
                session_id=request.session_id,
                model=meta.get("model", "groq"),
                input_tokens=meta.get("input_tokens", 0),
                output_tokens=meta.get("output_tokens", 0),
                embed_latency_ms=meta.get("embed_latency_ms", 0.0),
                search_latency_ms=meta.get("search_latency_ms", 0.0),
                rerank_latency_ms=meta.get("rerank_latency_ms", 0.0),
                generation_latency_ms=meta.get("generation_latency_ms", 0.0),
                total_latency_ms=meta.get("total_latency_ms", 0.0),
                chunks_sent=chunks_list,
                citations=citations_list,
                cache_hit=meta.get("cache_hit", False),
                rewritten_query=meta.get("rewritten_query", ""),
                cache_latency_saved_ms=meta.get("latency_saved_ms", 0.0),
            )
        except Exception as db_err:
            logger.warning("chat_turn_db_persistence_failed", error=str(db_err))

        return response
    except RetrievalError as e:
        raise HTTPException(status_code=503, detail=f"Retrieval error: {e.message}")
    except GenerationError as e:
        raise HTTPException(status_code=503, detail=f"Generation error: {e.message}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# --- Session & Conversation Endpoints (ChatGPT Style) ---

@router.get("/sessions")
async def list_user_sessions(
    username: str = "test1",
    role: Optional[str] = None,
    filter_user: Optional[str] = None,
):
    """Get conversation sessions.
    - If role == 'admin' and no filter_user or filter_user == 'all': returns all sessions across all users.
    - If role == 'admin' and filter_user specified: returns all sessions for that user.
    - If role != 'admin': strictly returns ONLY sessions belonging to the authenticated username.
    """
    try:
        chat_repo = ChatRepository()
        if role == "admin":
            if filter_user and filter_user != "all":
                sessions = chat_repo.get_all_sessions(limit=100, user_filter=filter_user)
            else:
                sessions = chat_repo.get_all_sessions(limit=100)
        else:
            # Non-admin user can ONLY see their own sessions
            sessions = chat_repo.get_user_sessions(username=username)
        return {"username": username, "role": role or "user", "sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch sessions: {str(e)}")


@router.get("/sessions/{session_id}")
async def get_session_history(
    session_id: str,
    username: Optional[str] = None,
    role: Optional[str] = None,
    session_user: Optional[str] = None,
):
    """Get all messages in a conversation session in chronological order.
    Enforces privacy: non-admin users can only view messages from their own sessions.
    """
    try:
        chat_repo = ChatRepository()
        filter_user = session_user or (username if role != "admin" else None)
        messages = chat_repo.get_session_messages(session_id=session_id, username=filter_user)
        
        # Access control: If non-admin user tries to access another user's session
        if role != "admin" and username and messages:
            session_owners = {m.get("username") for m in messages if m.get("username")}
            if session_owners and username not in session_owners:
                raise HTTPException(
                    status_code=403, 
                    detail="Access denied: You do not have permission to view another user's chat history."
                )

        return {"session_id": session_id, "messages": messages, "count": len(messages)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch session messages: {str(e)}")


@router.delete("/sessions/{session_id}")
async def delete_user_session(
    session_id: str, 
    username: Optional[str] = None,
    role: Optional[str] = None,
):
    """Delete a conversation session and all its messages."""
    try:
        chat_repo = ChatRepository()
        # Admin can delete any session; non-admin can only delete their own
        owner_filter = None if role == "admin" else username
        success = chat_repo.delete_session(session_id=session_id, username=owner_filter)
        return {"session_id": session_id, "deleted": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")


# --- Document Management Endpoints ---

@router.post("/ingest", response_model=IngestionResult)
async def ingest_documents(input: IngestInput):
    """Ingest documents from a file path or directory.

    Runs the full ingestion pipeline: load → clean → chunk → embed → store.
    """
    pipeline = IngestionPipeline()
    retriever = get_retriever()

    try:
        request = IngestionRequest(
            path=input.path,
            document_version=input.document_version,
            metadata=input.metadata,
        )

        path = request.resolved_path

        if path.is_file():
            chunks = pipeline.ingest_file(path, input.document_version, input.metadata)
            indexed = retriever.index(chunks)
            return IngestionResult(
                documents_processed=1,
                chunks_created=len(chunks),
                chunks_embedded=indexed,
                document_ids=[chunks[0].document_id] if chunks else [],
            )
        elif path.is_dir():
            result = pipeline.ingest_directory(path, input.document_version, input.metadata)
            # Also index all chunks
            for file_path in sorted(path.rglob("*")):
                if file_path.suffix.lower() in {".pdf", ".html", ".htm", ".md", ".markdown"}:
                    try:
                        chunks = pipeline.ingest_file(file_path, input.document_version, input.metadata)
                        retriever.index(chunks)
                        result.chunks_embedded += len(chunks)
                    except Exception:
                        continue
            return result
        else:
            raise HTTPException(status_code=400, detail=f"Path not found: {input.path}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("/documents/count")
async def get_document_count():
    """Get the total number of indexed document chunks, reconciling with disk first."""
    try:
        from ragops.storage.repositories import DocumentCatalogRepository
        DocumentCatalogRepository().reconcile_with_disk(auto_embed=False)
    except Exception:
        pass
    retriever = get_retriever()
    return {"count": retriever.document_count}


@router.get("/catalog")
async def get_document_catalog(doc_type: Optional[str] = None):
    """Get the auto-classified document inventory and classification summary, auto-reconciled with data/raw."""
    try:
        from ragops.storage.repositories import DocumentCatalogRepository
        repo = DocumentCatalogRepository()
        documents = repo.list_documents(doc_type=doc_type, auto_reconcile=True)
        summary = repo.get_summary()
        return {
            "summary": summary,
            "documents": documents,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch catalog: {str(e)}")


@router.post("/catalog/sync")
async def sync_catalog_with_disk(auto_embed: bool = False):
    """Explicitly reconcile physical files in data/raw with PostgreSQL/SQLite and ChromaDB vector store."""
    try:
        from ragops.storage.repositories import DocumentCatalogRepository
        repo = DocumentCatalogRepository()
        reconcile_result = repo.reconcile_with_disk(auto_embed=auto_embed)
        documents = repo.list_documents(auto_reconcile=False)
        summary = repo.get_summary()
        return {
            "status": "success",
            "reconciliation": reconcile_result,
            "summary": summary,
            "documents": documents,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync catalog with disk: {str(e)}")


@router.post("/catalog/embed/{document_source}")
async def embed_single_document(document_source: str):
    """Ingest, chunk, and embed a pending document from data/raw into ChromaDB."""
    try:
        from ragops.storage.repositories import DocumentCatalogRepository
        repo = DocumentCatalogRepository()
        result = repo.embed_document(document_source)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("embed_single_document_failed", source=document_source, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to embed document: {str(e)}")


@router.post("/catalog/embed-all")
async def embed_all_pending_documents():
    """Batch embed all unembedded / pending documents in data/raw into ChromaDB."""
    try:
        from ragops.storage.repositories import DocumentCatalogRepository
        repo = DocumentCatalogRepository()
        result = repo.embed_all_pending()
        return result
    except Exception as e:
        logger.error("embed_all_pending_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to embed pending documents: {str(e)}")


@router.post("/catalog/upload")
async def upload_and_classify_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
):
    """Upload a new document (.pdf, .md, .txt) into data/raw, auto-classify, chunk, embed into ChromaDB, and record in DB."""
    filename = file.filename
    if not filename:
        raise HTTPException(status_code=400, detail="Filename missing from upload request.")

    # Determine document title: use provided title or default to original filename
    effective_title = title.strip() if title and title.strip() else filename

    suffix = Path(filename).suffix.lower()
    allowed_suffixes = {".pdf", ".md", ".markdown", ".txt", ".html", ".htm", ".docx"}
    if suffix not in allowed_suffixes:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{suffix}'. Supported formats: {', '.join(sorted(allowed_suffixes))}"
        )

    # 1. Save file directly to data/raw directory
    raw_dir = Path("data/raw").resolve()
    raw_dir.mkdir(parents=True, exist_ok=True)
    target_path = raw_dir / filename

    content = await file.read()
    with open(target_path, "wb") as f:
        f.write(content)

    logger.info("document_uploaded_saving_to_raw", filename=filename, title=effective_title, size_bytes=len(content))

    # 2. Ingest, auto-classify, chunk, and save metadata to PostgreSQL/SQLite
    try:
        pipeline = IngestionPipeline()
        chunks = pipeline.ingest_file(target_path, metadata={"custom_title": effective_title})
    except Exception as e:
        logger.error("ingestion_failed_for_upload", filename=filename, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to process and chunk document: {str(e)}")

    # 3. Index embeddings into ChromaDB vector store
    try:
        retriever = get_retriever()
        indexed_count = retriever.index(chunks) if hasattr(retriever, "index") else retriever.index_chunks(chunks)
    except Exception as e:
        logger.error("vector_indexing_failed", filename=filename, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to index embeddings in ChromaDB: {str(e)}")

    # 4. Fetch the synced classification record from database and persist custom title
    from ragops.storage.database import get_session
    from ragops.storage.models import DocumentModel
    session = get_session()
    doc_record = None
    try:
        doc_record = session.query(DocumentModel).filter(DocumentModel.source == filename).first()
        if doc_record:
            doc_record.title = effective_title
            doc_record.chunk_count = indexed_count
            meta = dict(doc_record.metadata_json or {})
            meta["is_embedded"] = True
            meta["file_size_bytes"] = len(content)
            doc_record.metadata_json = meta
            session.commit()
    finally:
        session.close()

    logger.info("document_upload_and_classification_complete", filename=filename, title=effective_title, chunks=len(chunks), indexed=indexed_count)

    return {
        "status": "success",
        "message": f"Successfully ingested and indexed '{filename}'.",
        "filename": filename,
        "title": effective_title,
        "doc_type": doc_record.doc_type if doc_record else "other",
        "category": doc_record.category if doc_record else "General Corporate",
        "governance_level": doc_record.governance_level if doc_record else "Operational",
        "is_policy": doc_record.is_policy if doc_record else False,
        "chunks_indexed": indexed_count,
        "file_size_bytes": len(content),
    }


@router.delete("/catalog/{document_source}")
async def delete_catalog_document(document_source: str):
    """Delete a document from physical disk (data/raw), remove its chunks from ChromaDB, and delete from DB."""
    try:
        from ragops.storage.repositories import DocumentCatalogRepository
        repo = DocumentCatalogRepository()
        result = repo.delete_document(document_source)
        return {
            "status": "success",
            "message": f"Deleted document '{document_source}', purged physical file, vector embeddings, and invalidated semantic cache.",
            "details": result,
        }
    except Exception as e:
        logger.error("delete_catalog_document_failed", document=document_source, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")




@router.get("/cache/stats")
async def get_cache_statistics():
    """Get semantic answer cache metrics (hits, hit rate, latency saved, cost saved)."""
    try:
        from ragops.storage.repositories import SemanticCacheRepository
        repo = SemanticCacheRepository()
        return repo.get_cache_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch cache stats: {str(e)}")


@router.get("/cache/entries")
async def list_cached_queries(limit: int = 50):
    """List cached queries with scopes, hit counts, and answer previews."""
    try:
        from ragops.storage.repositories import SemanticCacheRepository
        repo = SemanticCacheRepository()
        return {"entries": repo.list_entries(limit=limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list cache entries: {str(e)}")


@router.delete("/cache")
async def clear_semantic_cache():
    """Flush the semantic cache."""
    try:
        from ragops.storage.repositories import SemanticCacheRepository
        repo = SemanticCacheRepository()
        count = repo.clear_cache()
        # Also clear in-memory pipeline cache
        pipeline = get_rag_pipeline()
        if hasattr(pipeline, "_query_intel"):
            pipeline._query_intel._memory_cache.clear()
        return {"status": "cleared", "deleted_entries": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")
