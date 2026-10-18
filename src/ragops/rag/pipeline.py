"""RAG pipeline — the main orchestration layer.

Flow: Query → Transform → Retrieve → Rerank → Build Context → Generate → Response

This is the application-level layer connecting retrieval and generation.
Both the API and the evaluation system call this pipeline.
"""

from __future__ import annotations

import uuid

from ragops.core.logging import get_logger
from ragops.core.types import (
    QueryRequest,
    RAGResponse,
)
from ragops.generation.llm import GroqClient, LLMClient
from ragops.generation.prompts import build_system_prompt, build_user_prompt
from ragops.generation.response import ResponseBuilder
from ragops.rag.context_builder import ContextBuilder
from ragops.rag.query_transform import QueryTransformer
from ragops.retrieval.retriever import RAGRetriever

logger = get_logger(__name__)


class RAGPipeline:
    """Production RAG pipeline — the central orchestrator.

    Coordinates the full flow:
    1. Query transformation
    2. Retrieval (embed → search → rerank)
    3. Context building
    4. LLM generation
    5. Response construction with citations

    The evaluation system reuses this exact pipeline.
    """

    def __init__(
        self,
        retriever: RAGRetriever | None = None,
        llm_client: LLMClient | None = None,
        query_transformer: QueryTransformer | None = None,
        context_builder: ContextBuilder | None = None,
        response_builder: ResponseBuilder | None = None,
    ):
        self._retriever = retriever or RAGRetriever()
        if llm_client is not None:
            self._llm_client = llm_client
        else:
            try:
                self._llm_client = GroqClient()
            except Exception as e:
                logger.warning(
                    "groq_client_init_failed_fallback_to_mock",
                    error=str(e),
                )
                from ragops.generation.llm import MockLLMClient
                self._llm_client = MockLLMClient()

        self._query_transformer = query_transformer or QueryTransformer()
        self._context_builder = context_builder or ContextBuilder()
        self._response_builder = response_builder or ResponseBuilder()


    def query(self, request: QueryRequest) -> RAGResponse:
        """Execute the full RAG pipeline for a user query.

        This is the primary entry point for both API requests
        and evaluation runs.
        """
        trace_id = f"trace_{uuid.uuid4().hex[:12]}"
        logger.info("rag_pipeline_start", trace_id=trace_id, query=request.query[:80])

        # 1. Transform query
        processed_query = self._query_transformer.transform(request)

        # 2. Retrieve relevant context
        retrieved_context = self._retriever.retrieve(
            query=processed_query.search_query,
            top_k=request.top_k,
        )

        # 3. Build context for the prompt
        prompt_context = self._context_builder.build(
            query=processed_query.original,
            retrieved_context=retrieved_context,
        )

        # 4. Generate answer
        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(prompt_context)

        llm_response = self._llm_client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        # 5. Build final response with citations
        rag_response = self._response_builder.build(
            llm_response=llm_response,
            retrieved_context=retrieved_context,
            trace_id=trace_id,
        )

        try:
            from ragops.observability.metrics import get_metrics
            metrics = get_metrics()
            metrics.increment("ragops_queries_total")
            metrics.increment("ragops_tokens_input_total", value=float(llm_response.input_tokens))
            metrics.increment("ragops_tokens_output_total", value=float(llm_response.output_tokens))
            total_lat = rag_response.metadata.get("total_latency_ms", 0.0)
            if total_lat > 0:
                metrics.observe("ragops_query_latency_ms", total_lat)
        except Exception:
            pass

        logger.info(
            "rag_pipeline_complete",
            trace_id=trace_id,
            sources=len(rag_response.sources),
            total_latency_ms=rag_response.metadata.get("total_latency_ms"),
        )

        return rag_response

    @property
    def retriever(self) -> RAGRetriever:
        """Access the retriever (for indexing operations)."""
        return self._retriever
