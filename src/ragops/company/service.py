"""Universal Company Intelligence Service orchestrating crawling, AI search gap-filling,
candidate fact persistence in PostgreSQL, human review, and vector index publication.
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Any, Optional

from ragops.company.agent import CompanyResearchAgent
from ragops.company.crawler import UniversalCompanyCrawler
from ragops.company.extractor import UniversalCompanyExtractor
from ragops.company.schema import AnalysisResult, CandidateFactItem
from ragops.core.logging import get_logger
from ragops.storage.repositories import FactManagementRepository

logger = get_logger(__name__)


class CompanyIntelligenceService:
    """Universal Enterprise Service:
    - Multi-page corporate website crawling
    - AI search gap-filling
    - Candidate facts & evidence staging in PostgreSQL
    - Human-in-the-loop review decisions
    - Transactional vector store outbox publishing.
    """

    def __init__(
        self,
        crawler: Optional[UniversalCompanyCrawler] = None,
        agent: Optional[CompanyResearchAgent] = None,
        extractor: Optional[UniversalCompanyExtractor] = None,
        repository: Optional[FactManagementRepository] = None,
    ):
        self.crawler = crawler or UniversalCompanyCrawler(max_pages=7)
        self.agent = agent or CompanyResearchAgent()
        self.extractor = extractor or UniversalCompanyExtractor()
        self.repository = repository or FactManagementRepository()

    def analyze_company_website(
        self,
        url: str,
        company_name: Optional[str] = None,
        organization_id: Optional[str] = None,
        max_pages: int = 7,
        fill_gaps: bool = True,
    ) -> AnalysisResult:
        """Execute end-to-end universal corporate intelligence workflow for ANY company."""
        clean_url = url.strip()
        if not clean_url.startswith(("http://", "https://")):
            clean_url = "https://" + clean_url

        # Infer company name from domain if not provided
        derived_name = company_name
        if not derived_name:
            domain = urllib.parse.urlparse(clean_url).netloc
            domain = domain.replace("www.", "").split(".")[0]
            derived_name = domain.capitalize()

        # Derive tenant organization ID if not provided
        org_id = organization_id
        if not org_id:
            org_id = re.sub(r"[^a-zA-Z0-9_-]", "_", derived_name.lower())

        logger.info(
            "universal_company_analysis_started",
            url=clean_url,
            company=derived_name,
            org_id=org_id,
            max_pages=max_pages,
            fill_gaps=fill_gaps,
        )

        # 1. Register corporate source in PostgreSQL
        source_rec = self.repository.register_source(
            display_name=f"{derived_name} Official Portal",
            source_url=clean_url,
            source_type="website",
            organization_id=org_id,
            verification_status="verified",
        )

        # 2. Multi-page web crawl
        crawler = UniversalCompanyCrawler(max_pages=max_pages)
        crawled_pages = crawler.crawl_website(clean_url)

        # 3. Store source documents in PostgreSQL with SHA-256 hashes
        doc_records = []
        for page in crawled_pages:
            doc_rec = self.repository.record_source_document(
                content_text=page.clean_text,
                canonical_url=page.url,
                title=page.title,
                source_id=source_rec["id"],
                organization_id=org_id,
            )
            doc_records.append(doc_rec)

        # Primary doc ID for candidates
        primary_doc_id = doc_records[0]["id"] if doc_records else None

        # 4. Autonomous Agent: Gap Analysis & AI Web Search Tool
        research_bundle = self.agent.analyze_and_fill_gaps(
            company_name=derived_name,
            crawled_docs=crawled_pages,
            enabled=fill_gaps,
        )

        # 5. Extract field-level candidate facts with exact citation evidence
        candidate_items = self.extractor.extract_candidates(
            company_name=derived_name,
            crawled_docs=crawled_pages,
            search_findings=research_bundle.get("search_findings", []),
            organization_id=org_id,
        )

        # 6. Persist candidate facts and citation evidence into PostgreSQL
        saved_candidates = []
        conflicts_count = 0

        for cand in candidate_items:
            if cand.validation_status == "conflicting":
                conflicts_count += 1

            saved = self.repository.save_candidate_with_evidence(
                section_key=cand.section_key,
                fact_key=cand.fact_key,
                proposed_value=cand.proposed_value,
                normalized_value=cand.normalized_value or cand.proposed_value,
                scope_key=cand.scope_key,
                document_id=primary_doc_id,
                validation_status=cand.validation_status,
                review_status="pending",
                extraction_confidence=cand.extraction_confidence,
                organization_id=org_id,
                evidence_list=[
                    {
                        "evidence_text": cand.evidence_text,
                        "section_heading": cand.section_heading,
                        "source_url": cand.source_url,
                    }
                ],
            )
            saved_candidates.append(saved)

        logger.info(
            "universal_company_analysis_saved_to_postgres",
            org_id=org_id,
            candidates_count=len(saved_candidates),
            conflicts=conflicts_count,
        )

        return AnalysisResult(
            organization_id=org_id,
            company_name=derived_name,
            root_url=clean_url,
            pages_crawled=len(crawled_pages),
            search_queries_executed=research_bundle.get("queries_executed", 0),
            candidates_count=len(saved_candidates),
            candidates=saved_candidates,
            conflicts_detected=conflicts_count,
            message=(
                f"Successfully crawled {len(crawled_pages)} pages and executed "
                f"{research_bundle.get('queries_executed', 0)} gap-filling searches. "
                f"Saved {len(saved_candidates)} candidate facts to PostgreSQL awaiting human review."
            ),
        )

    def list_tracked_companies(self) -> list[dict[str, Any]]:
        """List distinct companies and organizations tracked in PostgreSQL."""
        from ragops.storage.database import get_session
        from ragops.storage.models import CompanySourceModel, FactCandidateModel, CompanyFactModel
        from sqlalchemy import func

        session = get_session()
        try:
            # Query unique organizations
            org_rows = (
                session.query(
                    CompanySourceModel.organization_id,
                    CompanySourceModel.display_name,
                    CompanySourceModel.source_url,
                    func.count(CompanySourceModel.id).label("sources_count"),
                )
                .group_by(
                    CompanySourceModel.organization_id,
                    CompanySourceModel.display_name,
                    CompanySourceModel.source_url,
                )
                .all()
            )

            results = []
            seen_orgs = set()

            for org_id, display_name, source_url, _ in org_rows:
                if org_id in seen_orgs:
                    continue
                seen_orgs.add(org_id)

                cand_count = session.query(FactCandidateModel).filter(
                    FactCandidateModel.organization_id == org_id
                ).count()

                approved_count = session.query(CompanyFactModel).filter(
                    CompanyFactModel.organization_id == org_id,
                    CompanyFactModel.is_active == True,
                ).count()

                results.append({
                    "organization_id": org_id,
                    "company_name": display_name.replace(" Official Portal", "").replace(" Portal", ""),
                    "source_url": source_url,
                    "candidates_count": cand_count,
                    "approved_facts_count": approved_count,
                })

            return results
        finally:
            session.close()
