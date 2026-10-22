"""Universal Company Intelligence Package.

Provides autonomous multi-page crawling, AI search gap-filling,
field-level fact candidate extraction with citation evidence, PostgreSQL persistence,
human-in-the-loop review decisions, and reliable transactional vector index publication.
"""

from ragops.company.schema import (
    COMPANY_SECTIONS,
    AnalysisResult,
    CandidateFactItem,
    CrawledPageDoc,
)
from ragops.company.crawler import UniversalCompanyCrawler
from ragops.company.agent import CompanyResearchAgent
from ragops.company.extractor import UniversalCompanyExtractor
from ragops.company.service import CompanyIntelligenceService

__all__ = [
    "COMPANY_SECTIONS",
    "AnalysisResult",
    "CandidateFactItem",
    "CrawledPageDoc",
    "UniversalCompanyCrawler",
    "CompanyResearchAgent",
    "UniversalCompanyExtractor",
    "CompanyIntelligenceService",
]
