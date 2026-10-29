"""FastMCP Server for RAGOps — exposing knowledge base search, ingestion, traces, and cache telemetry.

Can be run standalone via stdio transport or invoked with `ragops mcp`.
Claude Desktop or any MCP client can integrate directly with this server.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from ragops.core.logging import get_logger

logger = get_logger(__name__)

# Import FastMCP / MCPServer safely
try:
    try:
        from mcp.server.fastmcp import FastMCP
    except (ImportError, ModuleNotFoundError):
        from mcp.server.mcpserver import MCPServer as FastMCP
except (ImportError, ModuleNotFoundError):
    FastMCP = None


def check_mcp_available() -> bool:
    """Check if the official MCP SDK is installed."""
    return FastMCP is not None


def create_mcp_server() -> Any:
    """Create and configure the RAGOps MCP server with tools."""
    if not check_mcp_available():
        raise ImportError(
            "The 'mcp' package is required to run the RAGOps MCP server.\n"
            "Install it via: pip install mcp"
        )

    server = FastMCP(
        name="RAGOps",
        instructions="RAGOps Enterprise Knowledge Platform — Semantic search, document ingestion, and telemetry.",
    )

    @server.tool()
    def search_knowledge_base(query: str, top_k: int = 5) -> dict[str, Any]:
        """Search the enterprise knowledge base with semantic retrieval, reranking, and grounded answer generation.

        Args:
            query: User's question or search query (1 to 1000 characters).
            top_k: Number of relevant chunks to retrieve (1 to 20, default 5).
        """
        clean_query = (query or "").strip()
        if not clean_query:
            return {"status": "error", "error": "Query cannot be empty."}
        if len(clean_query) > 1000:
            return {"status": "error", "error": "Query exceeds maximum allowed length of 1000 characters."}

        effective_top_k = max(1, min(int(top_k), 20))

        try:
            from ragops.core.types import QueryRequest
            from ragops.rag.pipeline import RAGPipeline

            pipeline = RAGPipeline()
            req = QueryRequest(query=clean_query, top_k=effective_top_k)
            resp = pipeline.query(req)

            citations_data = []
            for s in resp.sources:
                citations_data.append({
                    "document_id": s.chunk_id,
                    "document_name": s.document,
                    "page": s.page,
                    "section": s.section,
                    "text": s.text,
                    "score": s.score,
                })

            return {
                "status": "success",
                "query": clean_query,
                "answer": resp.answer,
                "citations": citations_data,
                "provider_used": resp.metadata.get("provider_used", "unknown"),
                "fallback_used": resp.metadata.get("fallback_used", False),
                "cache_hit": resp.metadata.get("cache_hit", False),
                "latency_ms": resp.metadata.get("total_latency_ms", 0.0),
            }
        except Exception as e:
            logger.error("mcp_search_failed", query=clean_query, error=str(e))
            return {
                "status": "error",
                "error": f"Search failed: {str(e)}",
                "how_to_fix": "Verify that your LLM provider and vector database are operational with 'ragops doctor'.",
            }

    @server.tool()
    def list_documents() -> dict[str, Any]:
        """List all indexed documents, chunk counts, and total inventory in the knowledge base."""
        try:
            from ragops.retrieval.retriever import RAGRetriever

            retriever = RAGRetriever()
            inventory = retriever.get_document_inventory()
            chunk_counts = retriever.get_document_chunk_counts()

            return {
                "status": "success",
                "total_documents": len(inventory),
                "total_chunks": retriever.document_count,
                "documents": [
                    {
                        "document_name": doc,
                        "chunks": chunk_counts.get(doc, 0),
                    }
                    for doc in inventory
                ],
            }
        except Exception as e:
            logger.error("mcp_list_documents_failed", error=str(e))
            return {
                "status": "error",
                "error": f"Failed to list documents: {str(e)}",
            }

    @server.tool()
    def ingest_document(path: str) -> dict[str, Any]:
        """Ingest and index a document from the data/raw directory into the RAG vector store.

        Path traversal is prevented: only files strictly located within 'data/raw/' are permitted.

        Args:
            path: Relative or absolute path to a document located in 'data/raw/'.
        """
        raw_dir = Path("data/raw").resolve()
        input_path = Path(path)

        if input_path.is_absolute():
            resolved = input_path.resolve()
        else:
            # If the user used '..' or path contains parent references, resolve directly from cwd
            if ".." in input_path.parts:
                resolved = (Path.cwd() / input_path).resolve()
            elif str(input_path).replace("\\", "/").startswith("data/raw"):
                resolved = (Path.cwd() / input_path).resolve()
            else:
                resolved = (raw_dir / input_path).resolve()

        # Strict path traversal check: MUST be strictly inside raw_dir
        try:
            resolved.relative_to(raw_dir)
        except ValueError:
            return {
                "status": "error",
                "error": "Access denied: Path traversal detected. Files must reside strictly inside the 'data/raw' directory.",
                "allowed_directory": str(raw_dir),
            }

        if not resolved.exists() or not resolved.is_file():
            return {
                "status": "error",
                "error": f"Document file not found: {resolved.name}",
                "expected_location": str(raw_dir),
            }

        try:
            from ragops.ingestion.pipeline import IngestionPipeline
            from ragops.retrieval.retriever import RAGRetriever

            ingestion = IngestionPipeline()
            chunks = ingestion.ingest_file(resolved)

            retriever = RAGRetriever()
            indexed_count = retriever.index_chunks(chunks)

            return {
                "status": "success",
                "document_name": resolved.name,
                "chunks_created": len(chunks),
                "chunks_indexed": indexed_count,
            }
        except Exception as e:
            logger.error("mcp_ingest_failed", path=str(resolved), error=str(e))
            return {
                "status": "error",
                "error": f"Ingestion failed: {str(e)}",
                "how_to_fix": "Verify that the document format is supported (.pdf, .md, .html) and not corrupted.",
            }

    @server.tool()
    def get_trace(trace_id: str) -> dict[str, Any]:
        """Retrieve detailed execution trace, tokens, latencies, and chunk provenance for a specific query.

        Args:
            trace_id: Unique trace ID generated during query execution.
        """
        clean_trace_id = (trace_id or "").strip()
        if not clean_trace_id or len(clean_trace_id) > 128:
            return {
                "status": "error",
                "error": "A valid trace_id string (1 to 128 characters) is required.",
            }

        try:
            from ragops.storage.repositories import ChatRepository

            chat_repo = ChatRepository()
            trace_data = chat_repo.get_trace(clean_trace_id)

            if not trace_data:
                return {
                    "status": "not_found",
                    "trace_id": clean_trace_id,
                    "message": f"No trace record found matching ID '{clean_trace_id}'.",
                }

            return {
                "status": "success",
                "trace": trace_data,
            }
        except Exception as e:
            logger.error("mcp_get_trace_failed", trace_id=clean_trace_id, error=str(e))
            return {
                "status": "error",
                "error": f"Failed to fetch trace: {str(e)}",
            }

    @server.tool()
    def cache_stats() -> dict[str, Any]:
        """Fetch real-time statistics from the Redis semantic cache."""
        try:
            from ragops.storage.redis_cache import RedisSemanticCache

            cache = RedisSemanticCache()
            stats = cache.get_stats()
            return {
                "status": "success",
                "stats": stats,
            }
        except Exception as e:
            logger.error("mcp_cache_stats_failed", error=str(e))
            return {
                "status": "error",
                "error": f"Failed to fetch cache stats: {str(e)}",
            }

    return server


def run_stdio() -> None:
    """Launch the RAGOps MCP server using stdio transport."""
    if not check_mcp_available():
        print(
            "Error: The 'mcp' package is required to run the RAGOps MCP server.\n"
            "Install it with: pip install mcp\n"
            "Or: pip install ragops[mcp]",
            file=sys.stderr,
        )
        sys.exit(1)

    server = create_mcp_server()
    logger.info("ragops_mcp_server_starting_stdio")
    server.run(transport="stdio")


if __name__ == "__main__":
    run_stdio()
