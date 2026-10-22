"""Corporate Research Agent equipped with AI Web Search Tool for autonomous gap-filling."""

from __future__ import annotations

from typing import Any, Optional
from ragops.company.schema import CrawledPageDoc
from ragops.core.logging import get_logger
from ragops.tools.search_tool import WebSearchTool

logger = get_logger(__name__)


class CompanyResearchAgent:
    """Autonomous Research Agent that evaluates crawled page coverage and executes targeted
    web searches to fill critical corporate information gaps (leadership, headcount, clients,
    locations, logistics hubs).
    """

    def __init__(self, search_tool: Optional[WebSearchTool] = None):
        self.search_tool = search_tool or WebSearchTool(max_results=3)

    def analyze_and_fill_gaps(
        self,
        company_name: str,
        crawled_docs: list[CrawledPageDoc],
        enabled: bool = True,
    ) -> dict[str, Any]:
        """Inspect crawled page texts, identify missing factual categories, and execute searches to fill gaps."""
        all_text = " ".join(doc.clean_text for doc in crawled_docs).lower()
        search_findings: list[dict[str, Any]] = []
        gaps_identified: list[str] = []

        if not enabled:
            return {
                "search_findings": [],
                "gaps_identified": [],
                "queries_executed": 0,
            }

        logger.info("company_research_agent_assessing_gaps", company=company_name, pages_count=len(crawled_docs))

        # Check for core dimensions in crawled text
        gap_checks = [
            ("leadership", ["ceo", "chief executive", "managing director", "chairman", "president"], "leadership"),
            ("headquarters", ["headquarters", "head office", "corporate seat", "registered office"], "headquarters"),
            ("headcount", ["employees", "headcount", "workforce", "people", "staff"], "headcount"),
            ("plants", ["manufacturing plant", "production plant", "factories", "assembly plant"], "plants"),
            ("clients", ["oem", "clients", "customers", "partners", "john deere", "caterpillar", "cnh"], "clients"),
            ("hubs", ["logistics hub", "spare parts", "spares", "distribution hub", "warehouse"], "hubs"),
            ("financials", ["revenue", "turnover", "ebitda", "annual report", "financial year"], "financials"),
        ]

        queries_executed = 0

        for category, keywords, fact_type in gap_checks:
            # Check if keywords appear with sufficient density
            found_count = sum(1 for kw in keywords if kw in all_text)
            if found_count < 2:
                gaps_identified.append(category)
                logger.info("gap_detected_triggering_search", company=company_name, category=category)
                results = self.search_tool.search_company_fact(company_name, fact_type)
                queries_executed += 1
                if results:
                    search_findings.append({
                        "category": category,
                        "fact_type": fact_type,
                        "results": results,
                    })

        logger.info(
            "company_research_agent_completed",
            company=company_name,
            gaps=gaps_identified,
            queries_executed=queries_executed,
            findings_count=len(search_findings),
        )

        return {
            "search_findings": search_findings,
            "gaps_identified": gaps_identified,
            "queries_executed": queries_executed,
        }
