"""Company profile, source-backed facts, review-before-publish workflow, and vector index sync."""

from __future__ import annotations

from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ragops.core.logging import get_logger
from ragops.storage.repositories import CompanyRepository, FactManagementRepository
from ragops.tools.web_extractor import CompanyWebExtractor

logger = get_logger(__name__)

router = APIRouter(prefix="/company", tags=["company"])


# -----------------------------------------------------------------------------
# Pydantic Schemas for Request Validation
# -----------------------------------------------------------------------------

class SourceCreateRequest(BaseModel):
    display_name: str = Field(..., description="Human-readable title for website or document source")
    source_url: Optional[str] = Field(None, description="Official website URL")
    source_type: str = Field("website", description="'website' or 'upload'")
    country_code: Optional[str] = Field(None, description="ISO 2-letter country code (e.g. IT, IN)")
    language_code: str = Field("en", description="Language code")
    verification_status: str = Field("verified", description="'verified', 'pending', or 'rejected'")


class DocumentUploadRequest(BaseModel):
    title: str = Field(..., description="Document title")
    content_text: str = Field(..., description="Raw text extracted from document or PDF")
    source_url: Optional[str] = Field(None, description="Original source URL or file path")
    country_code: Optional[str] = Field(None, description="Country code")
    publication_date: Optional[str] = Field(None, description="Date of document publication")


class CandidateUpdateRequest(BaseModel):
    proposed_value: Any = Field(..., description="Edited candidate value")


class CandidateReviewRequest(BaseModel):
    decision: str = Field(..., description="'approved', 'rejected', or 'needs_changes'")
    reviewer_id: str = Field("admin", description="Reviewer identifier")
    submitted_value: Optional[Any] = Field(None, description="Optional edited value if reviewer modified it")
    reason: Optional[str] = Field(None, description="Audit note or rejection/conflict explanation")


class PublicationProcessRequest(BaseModel):
    limit: int = Field(20, description="Max outbox events to process per batch")


class CompanyProfileUpdateRequest(BaseModel):
    company_name: Optional[str] = None
    group_name: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    products: Optional[list[str]] = None
    employee_details: Optional[str] = None
    locations: Optional[list[Any]] = None
    ceo: Optional[str] = None
    directors: Optional[list[str]] = None
    domains_urls: Optional[list[str]] = None
    metadata_json: Optional[dict[str, Any]] = None


class DomainUrlRequest(BaseModel):
    url: str = Field(..., description="Corporate website or branch portal URL")


class ScrapeRequest(BaseModel):
    urls: Optional[list[str]] = Field(None, description="Optional list of URLs to scrape.")
    url: Optional[str] = Field(None, description="Optional single company URL to scrape.")


class ApproveAndEmbedRequest(BaseModel):
    company_name: Optional[str] = "Enterprise"
    group_name: Optional[str] = ""
    industry: Optional[str] = ""
    description: Optional[str] = ""
    products: Optional[list[str]] = None
    employee_details: Optional[str] = ""
    locations: Optional[list[Any]] = None
    ceo: Optional[str] = ""
    directors: Optional[list[str]] = None
    domains_urls: Optional[list[str]] = None
    metadata_json: Optional[dict[str, Any]] = None


class UniversalAnalyzeRequest(BaseModel):
    url: str = Field(..., description="Any corporate website URL (e.g. https://www.siemens.com or https://www.tatamotors.com)")
    company_name: Optional[str] = Field(None, description="Optional company name")
    organization_id: Optional[str] = Field(None, description="Optional tenant or organization identifier")
    max_pages: int = Field(6, ge=1, le=15, description="Number of internal pages to crawl")
    fill_gaps_with_search: bool = Field(True, description="Enable AI search tool to research missing corporate dimensions")


class SearchGapRequest(BaseModel):
    company_name: str = Field(..., description="Company name")
    fact_type: str = Field("leadership", description="Category: leadership, headquarters, headcount, plants, clients, hubs, products, financials")


class CompanyClearRequest(BaseModel):
    organization_id: Optional[str] = None
    clear_all: bool = True


def _clear_rag_caches():
    """Clear memory and database semantic answer cache so updated facts take effect immediately."""
    try:
        from ragops.storage.database import get_session
        from ragops.storage.models import SemanticCacheModel
        session = get_session()
        session.query(SemanticCacheModel).delete()
        session.commit()
        session.close()
    except Exception as e:
        logger.debug("clear_semantic_cache_skipped", error=str(e))


# -----------------------------------------------------------------------------
# Universal Multi-Company Autonomous Intelligence Endpoints
# -----------------------------------------------------------------------------

@router.post("/clear")
async def clear_company_data(request: Optional[CompanyClearRequest] = None):
    """Completely clear previous company knowledge, candidates, facts, sources, profile, vector embeddings, and semantic caches."""
    try:
        org_id = None
        if request and not request.clear_all and request.organization_id:
            org_id = request.organization_id

        repo = FactManagementRepository()
        deleted = repo.clear_company_knowledge(organization_id=org_id)

        try:
            extractor = CompanyWebExtractor()
            extractor.clear_company_embeddings()
        except Exception as emb_e:
            logger.debug("clear_company_embeddings_skipped", error=str(emb_e))

        _clear_rag_caches()

        return {
            "status": "success",
            "message": "All previous company information, facts, review candidates, embeddings, and caches cleared successfully.",
            "deleted": deleted,
        }
    except Exception as e:
        logger.error("clear_company_data_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to clear company data: {str(e)}")


@router.post("/universal/analyze")
async def analyze_universal_company(request: UniversalAnalyzeRequest):
    """Universal Autonomous Extraction: Multi-page site crawl + AI search gap-filler + candidate staging in PostgreSQL."""
    try:
        from ragops.company.service import CompanyIntelligenceService
        service = CompanyIntelligenceService()
        result = service.analyze_company_website(
            url=request.url,
            company_name=request.company_name,
            organization_id=request.organization_id,
            max_pages=request.max_pages,
            fill_gaps=request.fill_gaps_with_search,
        )
        _clear_rag_caches()
        return {
            "status": "success",
            "analysis": result.model_dump(),
        }
    except Exception as e:
        logger.error("universal_analyze_failed", error=str(e), url=request.url)
        raise HTTPException(status_code=500, detail=f"Universal analysis failed: {str(e)}")


@router.get("/universal/companies")
async def get_tracked_companies():
    """List all distinct companies and organizations tracked in PostgreSQL."""
    try:
        from ragops.company.service import CompanyIntelligenceService
        service = CompanyIntelligenceService()
        companies = service.list_tracked_companies()
        return {"status": "success", "companies": companies, "total": len(companies)}
    except Exception as e:
        logger.error("get_tracked_companies_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch tracked companies: {str(e)}")


@router.post("/universal/search-gap")
async def search_company_gap(request: SearchGapRequest):
    """Autonomous AI Search Tool: Query search engines for missing corporate dimensions."""
    try:
        from ragops.tools.search_tool import WebSearchTool
        tool = WebSearchTool()
        results = tool.search_company_fact(request.company_name, request.fact_type)
        return {
            "status": "success",
            "company_name": request.company_name,
            "fact_type": request.fact_type,
            "results": results,
            "total": len(results),
        }
    except Exception as e:
        logger.error("search_company_gap_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


class ClearCompanyRequest(BaseModel):
    organization_id: Optional[str] = Field(None, description="Organization ID to clear, or 'all'")


@router.post("/clear")
async def clear_company_data(request: Optional[ClearCompanyRequest] = None):
    """Clear all candidate facts, approved facts, documents, and outbox records."""
    try:
        repo = FactManagementRepository()
        org_id = request.organization_id if request else None
        result = repo.clear_company_knowledge(organization_id=org_id)
        _clear_rag_caches()
        return result
    except Exception as e:
        logger.error("clear_company_data_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to clear company data: {str(e)}")


# -----------------------------------------------------------------------------
# Source-Backed Fact Validation & Outbox Publication Endpoints
# -----------------------------------------------------------------------------

@router.get("/sources")
async def list_company_sources(organization_id: str = "default_org"):
    """List all registered official domains and uploaded sources."""
    try:
        repo = FactManagementRepository()
        sources = repo.get_sources(organization_id=organization_id)
        return {"status": "success", "sources": sources, "total": len(sources)}
    except Exception as e:
        logger.error("list_company_sources_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list company sources: {str(e)}")


@router.post("/sources")
async def register_company_source(request: SourceCreateRequest, organization_id: str = "default_org"):
    """Register a new official website or document repository source."""
    try:
        repo = FactManagementRepository()
        src = repo.register_source(
            display_name=request.display_name,
            source_url=request.source_url,
            source_type=request.source_type,
            country_code=request.country_code,
            language_code=request.language_code,
            organization_id=organization_id,
            verification_status=request.verification_status,
        )
        return {"status": "success", "source": src, "message": "Source registered successfully."}
    except Exception as e:
        logger.error("register_company_source_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to register company source: {str(e)}")


@router.post("/sources/{source_id}/sync")
async def sync_company_source(source_id: str, organization_id: str = "default_org"):
    """Queue a website crawl for a registered company source and store versioned document content."""
    try:
        repo = FactManagementRepository()
        result = repo.sync_source(source_id=source_id, organization_id=organization_id)
        return {"status": "success", "sync_result": result}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error("sync_company_source_failed", error=str(e), source_id=source_id)
        raise HTTPException(status_code=500, detail=f"Failed to sync source: {str(e)}")


@router.post("/documents")
async def record_document(request: DocumentUploadRequest, organization_id: str = "default_org"):
    """Store retrieved or uploaded document text with SHA-256 cryptographic hash and version tracking."""
    try:
        repo = FactManagementRepository()
        doc = repo.record_source_document(
            content_text=request.content_text,
            canonical_url=request.source_url,
            title=request.title,
            country_code=request.country_code,
            publication_date=request.publication_date,
            organization_id=organization_id,
        )
        return {"status": "success", "document": doc, "message": f"Document version {doc['content_version']} recorded."}
    except Exception as e:
        logger.error("record_document_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to record document: {str(e)}")


@router.get("/candidates")
async def get_fact_candidates(
    section_key: Optional[str] = Query(None, description="Filter by section (identity, workforce, locations, clients, hubs, products, overview, innovation)"),
    review_status: Optional[str] = Query(None, description="Filter by review status (pending, approved, rejected, needs_changes)"),
    validation_status: Optional[str] = Query(None, description="Filter by validation status (valid, conflicting, needs_review, invalid)"),
    organization_id: str = "default_org",
):
    """Retrieve field-level extracted fact candidates with citations, confidence, and validation status."""
    try:
        repo = FactManagementRepository()
        candidates = repo.get_candidates(
            organization_id=organization_id,
            section_key=section_key,
            review_status=review_status,
            validation_status=validation_status,
        )
        return {"status": "success", "candidates": candidates, "total": len(candidates)}
    except Exception as e:
        logger.error("get_fact_candidates_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve candidates: {str(e)}")


@router.patch("/candidates/{candidate_id}")
async def update_candidate_value(candidate_id: str, request: CandidateUpdateRequest, reviewer_id: str = "admin"):
    """Administrator edits proposed candidate value before or during review."""
    try:
        repo = FactManagementRepository()
        updated = repo.update_candidate_proposed_value(
            candidate_id=candidate_id,
            new_value=request.proposed_value,
            user_id=reviewer_id,
        )
        return {"status": "success", "candidate": updated, "message": "Candidate value updated successfully."}
    except Exception as e:
        logger.error("update_candidate_value_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update candidate: {str(e)}")


@router.post("/candidates/{candidate_id}/review")
async def review_candidate_field(candidate_id: str, request: CandidateReviewRequest):
    """Review decision (approve, reject, needs_changes) with transactional audit trail and outbox publication queue."""
    try:
        repo = FactManagementRepository()
        result = repo.review_candidate(
            candidate_id=candidate_id,
            decision=request.decision,
            reviewer_id=request.reviewer_id,
            submitted_value=request.submitted_value,
            reason=request.reason,
        )
        return {
            "status": "success",
            "decision": result["decision"],
            "candidate": result["candidate"],
            "approved_fact": result["approved_fact"],
            "message": f"Candidate status updated to '{request.decision}'.",
        }
    except Exception as e:
        logger.error("review_candidate_field_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to submit review decision: {str(e)}")


@router.get("/outbox")
async def get_publication_outbox(
    status: Optional[str] = Query(None, description="Filter by outbox status (pending, processing, completed, failed)"),
    limit: int = 50,
    organization_id: str = "default_org",
):
    """List pending and completed publication outbox events for safe vector indexing."""
    try:
        repo = FactManagementRepository()
        events = repo.get_outbox_events(organization_id=organization_id, status=status, limit=limit)
        return {"status": "success", "outbox_events": events, "total": len(events)}
    except Exception as e:
        logger.error("get_publication_outbox_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch publication outbox: {str(e)}")


@router.post("/publish-outbox/process")
async def process_outbox(request: Optional[PublicationProcessRequest] = None, organization_id: str = "default_org"):
    """Claim pending publication outbox events, synthesize structured grounding chunks, and update Vector Store."""
    try:
        repo = FactManagementRepository()
        limit = request.limit if request else 20
        result = repo.process_publication_outbox(organization_id=organization_id, limit=limit)
        _clear_rag_caches()
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error("process_outbox_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to process publication outbox: {str(e)}")


@router.get("/ingestion-jobs/{job_id}")
async def get_ingestion_job_status(job_id: str, organization_id: str = "default_org"):
    """Track processing and vector store indexing status for an outbox event or source document."""
    try:
        repo = FactManagementRepository()
        job = repo.get_ingestion_job(job_id=job_id, organization_id=organization_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Ingestion job '{job_id}' not found")
        return {"status": "success", "job": job}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_ingestion_job_failed", error=str(e), job_id=job_id)
        raise HTTPException(status_code=500, detail=f"Failed to get ingestion job: {str(e)}")


@router.get("/knowledge")
async def get_published_knowledge(
    section_key: Optional[str] = Query(None, description="Filter by section"),
    organization_id: str = "default_org",
):
    """Retrieve all active approved company facts currently feeding the RAG assistant."""
    try:
        repo = FactManagementRepository()
        facts = repo.get_approved_facts(organization_id=organization_id, section_key=section_key)
        return {"status": "success", "facts": facts, "total": len(facts)}
    except Exception as e:
        logger.error("get_published_knowledge_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch approved facts: {str(e)}")


@router.post("/seed-carraro")
async def seed_carraro_grounding(organization_id: str = "default_org", force_reset: bool = False):
    """Seed audited Carraro candidate facts and approved knowledge (Campodarsego Italy HQ, 3,795 workforce, 8 plants, OEM partners)."""
    try:
        repo = FactManagementRepository()
        result = repo.seed_carraro_knowledge(organization_id=organization_id, force_reset=force_reset)
        _clear_rag_caches()
        return result
    except Exception as e:
        logger.error("seed_carraro_grounding_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to seed Carraro knowledge: {str(e)}")


# -----------------------------------------------------------------------------
# Backward-Compatible Profile & Extraction Endpoints
# -----------------------------------------------------------------------------

@router.get("/profile")
async def get_company_profile():
    """Retrieve the dynamic enterprise profile from PostgreSQL."""
    try:
        repo = CompanyRepository()
        profile = repo.get_profile()
        return {"profile": profile}
    except Exception as e:
        logger.error("get_company_profile_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch company profile: {str(e)}")


@router.put("/profile")
async def update_company_profile(request: CompanyProfileUpdateRequest):
    """Update company details, products, locations, or leadership in PostgreSQL and re-embed into Vector Store."""
    try:
        repo = CompanyRepository()
        data = request.model_dump(exclude_unset=True)
        updated = repo.update_profile(data)

        # Re-embed updated profile into Vector Store
        extractor = CompanyWebExtractor()
        chunks_embedded = extractor.embed_company_profile(updated)
        _clear_rag_caches()

        return {
            "status": "success",
            "profile": updated,
            "chunks_embedded": chunks_embedded,
            "message": f"Profile saved to PostgreSQL and {chunks_embedded} knowledge chunks embedded into Vector Store.",
        }
    except Exception as e:
        logger.error("update_company_profile_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update company profile: {str(e)}")


@router.post("/urls")
async def add_company_url(request: DomainUrlRequest):
    """Register a new corporate URL, location link, or MNC domain."""
    try:
        repo = CompanyRepository()
        updated = repo.add_domain_url(request.url)
        return {"status": "success", "domains_urls": updated.get("domains_urls", [])}
    except Exception as e:
        logger.error("add_company_url_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to add URL: {str(e)}")


@router.delete("/urls")
async def remove_company_url(request: DomainUrlRequest):
    """Remove a registered domain URL."""
    try:
        repo = CompanyRepository()
        updated = repo.remove_domain_url(request.url)
        return {"status": "success", "domains_urls": updated.get("domains_urls", [])}
    except Exception as e:
        logger.error("remove_company_url_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to remove URL: {str(e)}")


@router.post("/scrape-preview")
async def scrape_preview_urls(request: Optional[ScrapeRequest] = None):
    """Crawl URLs and extract company facts with Groq LLM for Admin Review before committing/embedding."""
    try:
        extractor = CompanyWebExtractor()
        target_urls = None
        if request:
            if request.urls:
                target_urls = request.urls
            elif request.url:
                target_urls = [request.url]
        result = extractor.crawl_and_extract_preview(urls=target_urls)
        return result
    except Exception as e:
        logger.error("scrape_preview_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to crawl and extract preview: {str(e)}")


@router.post("/approve-and-embed")
async def approve_and_embed_company_profile(request: ApproveAndEmbedRequest):
    """Admin confirmation: Save reviewed corporate profile to PostgreSQL and embed into ChromaDB Vector Store."""
    try:
        repo = CompanyRepository()
        data = request.model_dump(exclude_unset=True)
        updated = repo.update_profile(data)

        # Embed into vector store
        extractor = CompanyWebExtractor()
        chunks_embedded = extractor.embed_company_profile(updated)
        _clear_rag_caches()

        return {
            "status": "success",
            "message": f"Successfully verified corporate facts: Stored in PostgreSQL and embedded {chunks_embedded} knowledge chunks into Vector Store.",
            "profile": updated,
            "chunks_embedded": chunks_embedded,
        }
    except Exception as e:
        logger.error("approve_and_embed_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to approve and embed profile: {str(e)}")


@router.post("/reindex-embeddings")
async def reindex_company_embeddings():
    """Manually re-embed the current PostgreSQL corporate profile into the ChromaDB vector store."""
    try:
        repo = CompanyRepository()
        profile = repo.get_profile()
        extractor = CompanyWebExtractor()
        count = extractor.embed_company_profile(profile)
        _clear_rag_caches()
        return {
            "status": "success",
            "chunks_embedded": count,
            "message": f"Successfully embedded {count} corporate grounding chunks into Vector Store.",
        }
    except Exception as e:
        logger.error("reindex_embeddings_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to re-index company embeddings: {str(e)}")


@router.post("/scrape")
async def scrape_company_urls(request: Optional[ScrapeRequest] = None):
    """Crawl registered/provided MNC URLs, extract company details using Groq LLM, and update PostgreSQL + Vector Store."""
    try:
        extractor = CompanyWebExtractor()
        urls = request.urls if request and request.urls else None
        result = extractor.crawl_and_update(urls=urls)
        _clear_rag_caches()
        return result
    except Exception as e:
        logger.error("scrape_company_urls_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to crawl and extract company details: {str(e)}")
