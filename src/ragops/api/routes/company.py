"""Company profile, multi-URL MNC web crawler, and vector embedding API endpoints."""

from __future__ import annotations

from typing import Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ragops.core.logging import get_logger
from ragops.storage.repositories import CompanyRepository
from ragops.tools.web_extractor import CompanyWebExtractor

logger = get_logger(__name__)

router = APIRouter(prefix="/company", tags=["company"])


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
