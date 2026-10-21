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
from ragops.rag.query_intelligence import QueryIntelligenceEngine
from ragops.rag.query_transform import QueryTransformer
from ragops.retrieval.retriever import RAGRetriever

logger = get_logger(__name__)


class RAGPipeline:
    """Production RAG pipeline — the central orchestrator.

    Coordinates the full flow:
    1. Query intelligence (intent classification, scope safety gates, rewriting)
    2. Semantic answer caching
    3. Retrieval (embed → search → rerank)
    4. Context building
    5. LLM generation
    6. Response construction with citations
    7. Semantic cache persistence

    The evaluation system reuses this exact pipeline.
    """

    def __init__(
        self,
        retriever: RAGRetriever | None = None,
        llm_client: LLMClient | None = None,
        query_transformer: QueryTransformer | None = None,
        context_builder: ContextBuilder | None = None,
        response_builder: ResponseBuilder | None = None,
        query_intelligence: QueryIntelligenceEngine | None = None,
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
        self._query_intel = query_intelligence or QueryIntelligenceEngine()


    def query(self, request: QueryRequest) -> RAGResponse:
        """Execute the full RAG pipeline for a user query.

        Flow:
        1. Analyze intent and rewrite if shorthand/ambiguous
        2. Check semantic cache (with strict scope safety gates)
        3. If miss, run retrieval (vector + rerank)
        4. Detect collection-level enumeration needs
        5. Generate response with LLM
        6. Store validated response in semantic cache
        """
        trace_id = f"trace_{uuid.uuid4().hex[:12]}"
        logger.info("rag_pipeline_start", trace_id=trace_id, query=request.query[:80])

        # Fetch multi-turn conversation history for session continuity
        chat_history = list(request.chat_history) if request.chat_history else []
        if not chat_history and request.session_id:
            try:
                from ragops.storage.repositories import ChatRepository
                recent_msgs = ChatRepository().get_session_messages(request.session_id)
                # Take last 3 completed turns
                chat_history = [
                    {"query": m["query"], "answer": m["answer"]}
                    for m in recent_msgs[-3:]
                    if m.get("query") and m.get("answer")
                ]
            except Exception as hist_err:
                logger.debug("failed_to_load_session_history", error=str(hist_err))

        # 1. Query Intelligence Layer (Intent, scope, multi-turn rewriting)
        intent = self._query_intel.analyze_and_rewrite(request.query, chat_history=chat_history)

        # Conversational Chitchat & Acknowledgment handling (e.g. "ohk", "thanks", "hello")
        if intent.scope == "conversational":
            comp_name = "Enterprise"
            try:
                from ragops.storage.repositories import CompanyRepository
                prof = CompanyRepository().get_profile()
                if prof and prof.get("company_name"):
                    comp_name = prof["company_name"]
            except Exception:
                pass

            if intent.intent_type == "conversational_greeting":
                reply = f"Hello! I am your RAGOps corporate assistant for {comp_name}. How can I help you navigate our company facts, locations, policies, codes of conduct, or governance guidelines today?"
            elif intent.intent_type == "conversational_acknowledgment":
                reply = "You're welcome! Feel free to ask if you have any questions about company operations, locations, clients, policies, or procedures."
            else:
                reply = "Please enter a specific question or topic to search across the knowledge base (e.g. 'What are all company locations?', 'Who are key clients?', or 'POSH complaint procedure')."

            return RAGResponse(
                query=request.query,
                answer=reply,
                sources=[],
                trace_id=trace_id,
                metadata={
                    "retrieval_method": "conversational_direct",
                    "intent": intent.intent_type,
                    "scope": intent.scope,
                    "cache_hit": False,
                    "total_latency_ms": 1.0,
                    "total_tokens": 0,
                    "cost_usd": 0.0,
                    "session_id": request.session_id,
                },
            )

        # 2. Semantic Answer Cache Check (Exact & embedding-similarity with scope safety gates)
        cached_response = self._query_intel.check_cache(request.query, intent)
        if cached_response is not None:
            cached_response.metadata["trace_id"] = trace_id
            cached_response.metadata["session_id"] = request.session_id or ""
            logger.info(
                "rag_pipeline_cache_hit_returned",
                trace_id=trace_id,
                intent=intent.intent_type,
                scope=intent.scope,
            )
            return cached_response

        # 3. Transform query (use rewritten query if available for enhanced retrieval)
        query_for_search = intent.rewritten_query if intent.is_rewritten else request.query
        processed_query = self._query_transformer.transform(
            QueryRequest(query=query_for_search, top_k=request.top_k, filters=request.filters)
        )

        # 4. Retrieve relevant context
        retrieved_context = self._retriever.retrieve(
            query=processed_query.search_query,
            top_k=request.top_k,
        )

        # Dynamic Web & Company Profile Tool:
        # If user asks about locations, clients, products, employees, founding background, or live facts,
        # synthesize dynamic context from PostgreSQL profile and registered MNC URLs
        try:
            from ragops.tools.web_extractor import CompanyWebExtractor
            from ragops.core.types import RetrievedChunk
            web_tool = CompanyWebExtractor()
            active_q = intent.rewritten_query if intent.is_rewritten else processed_query.original
            web_chunks = web_tool.fetch_dynamic_web_context(query=active_q, top_n_chunks=4)
            if web_chunks:
                priority_chunks = [
                    RetrievedChunk(
                        chunk_id=f"web_{abs(hash(wc['text'][:40])) % 1000000}",
                        document_id=wc.get("document", "Corporate Profile"),
                        text=wc["text"],
                        score=wc.get("score", 0.98),
                        source=wc["source"],
                        metadata={"url": wc.get("url", ""), "provenance": "dynamic_corporate_tool", "is_priority": True},
                    )
                    for wc in web_chunks
                ]
                # Prepend dynamic corporate chunks to top of context so they are never sliced away
                retrieved_context.chunks = priority_chunks + retrieved_context.chunks
        except Exception as web_err:
            logger.debug("dynamic_web_lookup_skipped", error=str(web_err))


        # 5. Detect collection-wide enumeration queries
        q_lower = (intent.rewritten_query if intent.is_rewritten else processed_query.original).lower()
        is_collection_query = (
            intent.intent_type in ("collection_count", "collection_inventory")
            or intent.scope == "collection_wide"
            or any(k in q_lower for k in [
                "every unique document", "all documents", "list every", "list all",
                "how many policies", "distinct company policies", "how many documents",
                "classify each", "document inventory", "distinct policies", "all policies",
                "list every unique", "total documents", "unique document title",
                "entire collection", "across all documents", "classify each as a policy"
            ])
        )

        inventory = None
        if is_collection_query:
            inventory = self._retriever.get_document_inventory()
            logger.info("collection_inventory_injected", count=len(inventory))

        # 6. Build context for the prompt (including chat history for multi-turn coherence)
        prompt_context = self._context_builder.build(
            query=intent.rewritten_query if intent.is_rewritten else processed_query.original,
            retrieved_context=retrieved_context,
            inventory=inventory,
            chat_history=chat_history,
        )

        # 7. Generate answer
        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(prompt_context)

        llm_response = self._llm_client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=4096 if is_collection_query else 2048,
        )

        # 8. Build final response with citations
        rag_response = self._response_builder.build(
            llm_response=llm_response,
            retrieved_context=retrieved_context,
            trace_id=trace_id,
        )

        # Attach Query Intelligence metadata
        rag_response.metadata["intent"] = intent.intent_type
        rag_response.metadata["scope"] = intent.scope
        rag_response.metadata["target_entity"] = intent.target_entity
        rag_response.metadata["is_rewritten"] = intent.is_rewritten
        if intent.is_rewritten:
            rag_response.metadata["rewritten_query"] = intent.rewritten_query

        # 9. Persist to Semantic Cache for future reuse
        self._query_intel.store_in_cache(
            query=request.query,
            intent=intent,
            response=rag_response,
            retrieved_chunks=retrieved_context.chunks,
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
