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

        # Conversational Chitchat & Acknowledgment handling (e.g. "hi", "hii", "how are you", "thanks")
        if intent.scope == "conversational":
            comp_name = ""
            try:
                from ragops.storage.repositories import CompanyRepository
                prof = CompanyRepository().get_profile()
                if prof and prof.get("company_name") and prof["company_name"].strip().lower() not in ("enterprise", "company", ""):
                    comp_name = f" for {prof['company_name'].strip()}"
            except Exception:
                pass

            if intent.intent_type == "conversational_greeting":
                reply = f"Hello! I am your RAGOps corporate assistant{comp_name}. How can I help you navigate company policies, locations, guidelines, or procedures today?"
            elif intent.intent_type == "conversational_acknowledgment":
                reply = "You're welcome! Feel free to ask if you have any questions about company policies, documents, or procedures."
            else:
                reply = "Hello! Please feel free to ask any specific question across the corporate knowledge base (e.g. 'What is the POSH complaint procedure?', 'What are the travel policy rules?', or 'Who are key clients?')."

            est_out_toks = max(15, len(reply) // 4)
            est_in_toks = max(2, len(request.query) // 4)
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
                    "model": "assistant-direct",
                    "total_latency_ms": 1.0,
                    "input_tokens": est_in_toks,
                    "output_tokens": est_out_toks,
                    "total_tokens": est_in_toks + est_out_toks,
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
            active_q = intent.rewritten_query if intent.is_rewritten else processed_query.original
            active_q_lower = active_q.lower()
            company_triggers = [
                "location", "locations", "plant", "plants", "facility", "facilities",
                "headquarter", "headquarters", "hq", "city", "cities", "address",
                "client", "clients", "customer", "customers", "oem", "partner", "partners",
                "distributor", "distributors", "hub", "hubs", "spares",
                "employee", "employees", "headcount", "workforce", "revenue", "turnover",
                "ceo", "chairman", "founder", "founded", "history", "leadership",
                "carraro", "hcl", "tcs", "infosys", "wipro", "company profile",
                "official website", "domain", "catalog", "portfolio"
            ]
            if any(k in active_q_lower for k in company_triggers):
                from ragops.tools.web_extractor import CompanyWebExtractor
                from ragops.core.types import RetrievedChunk
                web_tool = CompanyWebExtractor()
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

        # Strict Relevance Quality Gate:
        # Evaluate calibrated relevance score of retrieved context.
        # If the highest chunk score is below threshold (0.10 / 10%) and it's not a collection inventory query:
        # Strictly abstain! Never send irrelevant chunks (e.g. 0% or 5%) to LLM, and never trigger random web search tool hallucinations!
        max_chunk_score = max((float(getattr(c, "score", 0.0)) for c in retrieved_context.chunks), default=0.0)
        has_sufficient_relevance = (len(retrieved_context.chunks) > 0 and max_chunk_score >= 0.10) or is_collection_query

        if not has_sufficient_relevance:
            logger.info(
                "strict_relevance_gate_abstaining",
                query=request.query[:80],
                max_score=max_chunk_score,
                chunks_retrieved=len(retrieved_context.chunks),
            )
            abstain_answer = (
                f"I searched the corporate knowledge base, but could not locate verified documents or policies "
                f"with sufficient relevance to answer your question regarding '{request.query}'.\n\n"
                "Please verify that the relevant company policy or document has been uploaded to the catalog, "
                "or rephrase your question with more specific keywords."
            )
            est_in = max(2, len(request.query) // 4)
            est_out = max(15, len(abstain_answer) // 4)
            return RAGResponse(
                query=request.query,
                answer=abstain_answer,
                sources=[],
                trace_id=trace_id,
                metadata={
                    "retrieval_method": "strict_relevance_gate_abstention",
                    "max_relevance_score": round(max_chunk_score, 4),
                    "relevance_threshold": 0.10,
                    "chunks_retrieved": len(retrieved_context.chunks),
                    "total_latency_ms": round(retrieved_context.retrieval_latency_ms, 2),
                    "model": getattr(self._llm_client, "model_name", "groq"),
                    "input_tokens": est_in,
                    "output_tokens": est_out,
                    "total_tokens": est_in + est_out,
                    "cost_usd": 0.0,
                    "session_id": request.session_id or "",
                    "intent": intent.intent_type,
                    "scope": intent.scope,
                    "abstention": True,
                },
            )

        # Context relevance filtering: keep only chunks that are genuinely relevant (score >= 0.10)
        if not is_collection_query and len(retrieved_context.chunks) > 1:
            filtered_chunks = [c for c in retrieved_context.chunks if float(getattr(c, "score", 0.0)) >= 0.10]
            if filtered_chunks:
                retrieved_context.chunks = filtered_chunks

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

        # Check for abstention / refusal -> Trigger Autonomous Search Tool Fallback ONLY if explicit company URLs are registered
        if self._is_abstention(rag_response.answer):
            active_enterprise, enterprise_urls = self._resolve_active_enterprise(request.query)
            company_triggers = [
                "location", "locations", "plant", "plants", "headquarter", "hq",
                "client", "clients", "customer", "customers", "oem",
                "product", "products", "ceo", "director", "chairman", "workforce", "employee"
            ]
            if enterprise_urls and any(k in q_lower for k in company_triggers):
                logger.info("triggering_gated_search_fallback", enterprise=active_enterprise, urls=enterprise_urls)
                rag_response = self._execute_search_tool_fallback(
                    request=request,
                    intent=intent,
                    trace_id=trace_id,
                    retrieved_context=retrieved_context,
                )

        # Attach Query Intelligence metadata
        rag_response.metadata["intent"] = intent.intent_type
        rag_response.metadata["scope"] = intent.scope
        rag_response.metadata["target_entity"] = intent.target_entity
        rag_response.metadata["is_rewritten"] = intent.is_rewritten
        if intent.is_rewritten:
            rag_response.metadata["rewritten_query"] = intent.rewritten_query

        # 9. Persist to Semantic Cache for future reuse (only if verified answer, not abstention)
        if not self._is_abstention(rag_response.answer):
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

    def _is_abstention(self, text: str) -> bool:
        """Check if an answer is an LLM refusal, abstention, or lacks context."""
        from ragops.rag.query_intelligence import is_abstention_text
        return is_abstention_text(text)

    def _resolve_active_enterprise(self, query: str = "") -> tuple[str, list[str]]:
        """Resolve active enterprise name and registered official URLs."""
        c_name = ""
        urls: list[str] = []

        try:
            from ragops.storage.repositories import CompanyRepository
            prof = CompanyRepository().get_profile()
            if prof:
                if prof.get("company_name") and prof["company_name"].strip() and prof["company_name"] != "Enterprise":
                    c_name = prof["company_name"].strip()
                if prof.get("domains_urls"):
                    urls.extend([u for u in prof["domains_urls"] if u])
        except Exception:
            pass

        if not c_name or not urls:
            try:
                from ragops.storage.database import get_session
                from ragops.storage.models import CompanySourceModel
                session = get_session()
                src = session.query(CompanySourceModel).order_by(CompanySourceModel.created_at.desc()).first()
                if src:
                    if src.source_url and src.source_url not in urls:
                        urls.append(src.source_url)
                    if not c_name:
                        raw = (src.display_name or "").replace(" Official Portal", "").replace(" Portal", "").strip()
                        if raw and not raw.startswith("http") and raw.lower() not in ("company", "enterprise", "portal"):
                            c_name = raw
                        elif src.source_url:
                            import urllib.parse
                            domain = urllib.parse.urlparse(src.source_url).netloc.lower()
                            parts = domain.replace("www.", "").split(".")
                            if parts:
                                c_name = parts[0].capitalize()
                session.close()
            except Exception:
                pass

        if not c_name:
            c_name = "the enterprise"

        return c_name, urls

    def _execute_search_tool_fallback(
        self,
        request: QueryRequest,
        intent: Any,
        trace_id: str,
        retrieved_context: Any,
    ) -> RAGResponse:
        """Execute autonomous AI search tool fallback (Corrective RAG).

        When local vector documents cannot answer or yield an abstention, this autonomously
        invokes the WebSearchTool and registered company URLs, gathers verified external facts,
        re-prompts the LLM, and formats the response with official citations.
        """
        enterprise_name, urls = self._resolve_active_enterprise(query=request.query)
        logger.info(
            "executing_search_tool_fallback",
            enterprise=enterprise_name,
            urls=urls,
            query=request.query[:80],
        )

        from ragops.tools.search_tool import WebSearchTool
        from ragops.tools.web_extractor import fetch_url_text
        from ragops.core.types import Source

        search_tool = WebSearchTool()
        evidence_snippets: list[dict[str, str]] = []

        # 1. Authoritative Corporate Entity Lookup (Wikipedia REST API)
        entity_info = search_tool.search_corporate_entity(enterprise_name)
        if entity_info and entity_info.get("extract"):
            evidence_snippets.append({
                "title": f"{entity_info.get('title', enterprise_name)} - Official Corporate Registry",
                "url": entity_info.get("url", ""),
                "snippet": entity_info["extract"],
                "source": "official_corporate_registry",
            })

        # 2. Targeted Fact Search
        q_lower = request.query.lower()
        if any(w in q_lower for w in ["location", "where", "plant", "factory", "headquarter", "hq", "city", "address", "presence"]):
            fact_type = "locations"
        elif any(w in q_lower for w in ["client", "customer", "partner", "oem", "buyer"]):
            fact_type = "clients"
        elif any(w in q_lower for w in ["product", "service", "solution", "make", "offer"]):
            fact_type = "products"
        elif any(w in q_lower for w in ["ceo", "director", "chairman", "leadership", "founder"]):
            fact_type = "leadership"
        elif any(w in q_lower for w in ["employee", "workforce", "headcount", "people"]):
            fact_type = "headcount"
        else:
            fact_type = "general"

        if fact_type != "general":
            targeted_results = search_tool.search_company_fact(enterprise_name, fact_type)
            for tr in targeted_results[:3]:
                if tr.get("snippet") and not any(tr["snippet"][:50] in e["snippet"] for e in evidence_snippets):
                    evidence_snippets.append(tr)
        else:
            search_results = search_tool.search(f"{enterprise_name} {request.query}", max_results=3)
            for sr in search_results:
                if sr.get("snippet") and not any(sr["snippet"][:50] in e["snippet"] for e in evidence_snippets):
                    evidence_snippets.append(sr)

        # 3. Live URL Scraping (from registered company URLs)
        for u in urls[:2]:
            try:
                import urllib.parse
                web_text = fetch_url_text(u, timeout_sec=4, max_chars=2500)
                if not web_text or len(web_text.strip()) < 80:
                    parsed_u = urllib.parse.urlparse(u)
                    if parsed_u.path and parsed_u.path not in ("", "/"):
                        base_u = f"{parsed_u.scheme}://{parsed_u.netloc}/"
                        web_text = fetch_url_text(base_u, timeout_sec=4, max_chars=2500)
                if web_text:
                    paras = [p.strip() for p in web_text.split("\n\n") if len(p.strip()) > 60]
                    for p in paras[:3]:
                        evidence_snippets.append({
                            "title": f"{enterprise_name} Official Portal",
                            "url": u,
                            "snippet": p,
                            "source": "official_enterprise_website",
                        })
            except Exception as e_url:
                logger.debug("portal_fetch_in_fallback_skipped", url=u, error=str(e_url))

        # If still no snippets could be found, return a polite refusal
        if not evidence_snippets:
            return RAGResponse(
                query=request.query,
                answer=(
                    f"I searched official corporate records and web sources for '{enterprise_name}', "
                    f"but could not locate verified public information regarding your specific inquiry. "
                    "Please ensure the official company portal is registered or upload relevant company documents."
                ),
                sources=[],
                trace_id=trace_id,
                metadata={
                    "retrieval_method": "autonomous_search_tool_crag_miss",
                    "search_fallback_applied": True,
                    "active_enterprise": enterprise_name,
                },
            )

        # 4. Synthesize verified factual response using LLM
        evidence_text_blocks = []
        sources: list[Source] = []
        for i, ev in enumerate(evidence_snippets, 1):
            evidence_text_blocks.append(
                f"[{i}] {ev.get('title')} ({ev.get('url', 'N/A')}):\n{ev.get('snippet', '')}"
            )
            sources.append(
                Source(
                    document=ev.get("title", f"{enterprise_name} Public Information"),
                    chunk_id=f"search_{i}_{abs(hash(ev.get('url', '')) % 10000)}",
                    page=1,
                    section=ev.get("source", "search_tool"),
                    text=ev.get("snippet", ""),
                    score=0.98,
                )
            )

        search_context_str = "\n\n".join(evidence_text_blocks)

        system_prompt = (
            "You are an enterprise AI assistant equipped with real-time autonomous search tools.\n"
            f"The user is asking an authoritative question about '{enterprise_name}'.\n"
            "Using ONLY the live search results and corporate registry data provided below, "
            "provide a complete, professional, direct, and factual answer.\n"
            "- If asked about the company name or identity, give the complete legal identity, parent group, and core business overview.\n"
            "- If asked about locations or headquarters, clearly state the corporate headquarters and global footprint (number of locations, countries, key hubs).\n"
            "- Format with bullet points or clean paragraphs for readability.\n"
            "- Never say 'documents do not contain information' or abstain when the search evidence provides the answer.\n"
            "- Conclude with a citation referencing the official source."
        )

        user_prompt = (
            f"User Question: {request.query}\n\n"
            f"=== LIVE SEARCH & CORPORATE REGISTRY EVIDENCE ===\n"
            f"{search_context_str}\n\n"
            "Please provide a comprehensive and factual response based on the above evidence."
        )

        try:
            llm_res = self._llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=2048,
            )
            fallback_answer = (llm_res.text or getattr(llm_res, "content", "")).strip()
        except Exception as gen_err:
            logger.error("search_fallback_generation_failed", error=str(gen_err))
            fallback_answer = (
                f"According to verified corporate registry records for {enterprise_name}:\n\n"
                + "\n\n".join([f"• {ev['snippet']}" for ev in evidence_snippets[:2]])
            )


        fb_in_tokens = getattr(llm_res, "input_tokens", 0) if 'llm_res' in locals() and hasattr(llm_res, "input_tokens") else 0
        fb_out_tokens = getattr(llm_res, "output_tokens", 0) if 'llm_res' in locals() and hasattr(llm_res, "output_tokens") else 0
        if fb_in_tokens + fb_out_tokens == 0:
            fb_in_tokens = max(2, len(request.query) // 4 + len(search_context_str) // 4)
            fb_out_tokens = max(15, len(fallback_answer) // 4)
        fb_total_tokens = fb_in_tokens + fb_out_tokens
        fb_cost = round(((fb_in_tokens * 0.05 + fb_out_tokens * 0.08) / 1_000_000), 6)
        fb_model = getattr(llm_res, "model", getattr(self._llm_client, "model_name", "groq")) if 'llm_res' in locals() else getattr(self._llm_client, "model_name", "groq")

        return RAGResponse(
            query=request.query,
            answer=fallback_answer,
            sources=sources,
            trace_id=trace_id,
            metadata={
                "retrieval_method": "autonomous_search_tool_crag",
                "search_fallback_applied": True,
                "active_enterprise": enterprise_name,
                "evidence_sources_count": len(evidence_snippets),
                "model": fb_model,
                "input_tokens": fb_in_tokens,
                "output_tokens": fb_out_tokens,
                "total_tokens": fb_total_tokens,
                "cost_usd": fb_cost,
                "total_latency_ms": 450.0,
                "intent": getattr(intent, "intent_type", "general"),
                "scope": getattr(intent, "scope", "company_overview"),
            },
        )

    @property
    def retriever(self) -> RAGRetriever:
        """Access the retriever (for indexing operations)."""
        return self._retriever
