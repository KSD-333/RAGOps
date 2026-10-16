"""Query routes — RAG query and document management endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ragops.api.dependencies import get_rag_pipeline, get_retriever
from ragops.core.exceptions import GenerationError, RetrievalError
from ragops.core.types import QueryRequest, RAGResponse
from ragops.ingestion.pipeline import IngestionPipeline
from ragops.ingestion.schemas import IngestionRequest, IngestionResult

router = APIRouter(tags=["query"])


# --- Request/Response Models ---

class QueryInput(BaseModel):
    """API-level query input."""
    query: str
    top_k: int = Field(default=5, ge=1, le=50)
    filters: dict = Field(default_factory=dict)


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
    """
    pipeline = get_rag_pipeline()

    request = QueryRequest(
        query=input.query,
        top_k=input.top_k,
        filters=input.filters,
    )

    try:
        response = pipeline.query(request)
        return response
    except RetrievalError as e:
        raise HTTPException(status_code=503, detail=f"Retrieval error: {e.message}")
    except GenerationError as e:
        raise HTTPException(status_code=503, detail=f"Generation error: {e.message}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


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
    """Get the total number of indexed document chunks."""
    retriever = get_retriever()
    return {"count": retriever.document_count}
