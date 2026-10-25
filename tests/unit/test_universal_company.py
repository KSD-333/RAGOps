"""Unit tests for Universal Company Intelligence package (crawler, search tool, agent, extractor)."""

import pytest
from ragops.company.crawler import UniversalCompanyCrawler
from ragops.company.agent import CompanyResearchAgent
from ragops.company.extractor import UniversalCompanyExtractor
from ragops.company.schema import CrawledPageDoc
from ragops.tools.search_tool import WebSearchTool


def test_web_search_tool_initialization():
    tool = WebSearchTool(max_results=3)
    assert tool.max_results == 3
    # Test query formatting
    res = tool.search_company_fact("Siemens", "leadership")
    assert isinstance(res, list)


def test_universal_crawler_link_prioritization():
    crawler = UniversalCompanyCrawler(max_pages=5)
    sample_links = [
        "https://www.example.com/en/about-us",
        "https://www.example.com/en/global-presence/plants",
        "https://www.example.com/en/products/transmissions",
        "https://www.example.com/privacy-policy",
        "https://www.example.com/terms",
        "https://www.example.com/en/leadership/ceo",
    ]
    prioritized = crawler._prioritize_links(sample_links, "example.com", set())
    assert len(prioritized) >= 4
    urls = [url for url, _ in prioritized]
    # Check that high-value sections are prioritized over generic privacy/terms
    assert any("about-us" in u for u in urls)
    assert any("plants" in u or "presence" in u for u in urls)
    assert any("products" in u for u in urls)


def test_company_research_agent_gap_detection():
    agent = CompanyResearchAgent()
    docs = [
        CrawledPageDoc(
            url="https://www.acme.com",
            title="Acme Corporation - Welcome",
            clean_text="Acme produces transmissions and precision gears.",
            char_count=60,
        )
    ]
    # Leadership and headcount are missing from this brief page
    res = agent.analyze_and_fill_gaps(company_name="Acme Corp", crawled_docs=docs, enabled=False)
    assert res["queries_executed"] == 0


def test_universal_extractor_heuristic_extraction():
    extractor = UniversalCompanyExtractor()
    sample_text = (
        "Acme International S.p.A. is headquartered in Milan, Italy. "
        "The Chief Executive Officer is John Doe. "
        "The company employs 4,500 people globally across 6 manufacturing plants. "
        "Key clients include John Deere and Caterpillar. "
        "Products include mechanical transmissions, axles, and electric powertrains."
    )
    docs = [
        CrawledPageDoc(
            url="https://www.acme.com/about",
            title="About Acme",
            clean_text=sample_text,
            char_count=len(sample_text),
        )
    ]
    candidates = extractor.extract_candidates(company_name="Acme Corp", crawled_docs=docs, search_findings=[])
    assert len(candidates) >= 4

    keys = {(c.section_key, c.fact_key) for c in candidates}
    assert ("identity", "legal_name") in keys
    assert ("identity", "global_headquarters") in keys or ("locations", "headquarters") in keys or ("locations", "headquarters_location") in keys
    assert (
        ("identity", "ceo") in keys
        or ("identity", "chief_executive_officer") in keys
        or ("leadership", "chief_executive_officer") in keys
        or ("leadership", "ceo") in keys
    )
    assert ("workforce", "global_headcount") in keys or ("workforce", "headcount") in keys


def test_conflict_detection_in_extractor():
    extractor = UniversalCompanyExtractor()
    from ragops.company.schema import CandidateFactItem

    cand1 = CandidateFactItem(
        section_key="workforce",
        fact_key="global_headcount",
        scope_key="global",
        proposed_value=3795,
        evidence_text="Global profile reports 3,795 people.",
        source_url="https://www.company.com/global",
        validation_status="valid",
    )
    cand2 = CandidateFactItem(
        section_key="workforce",
        fact_key="regional_headcount",
        scope_key="country:IN",
        proposed_value="1,592 facility count vs 1,700 narrative",
        evidence_text="Facility reports 1,592; narrative states >1,700.",
        source_url="https://www.company.com/india",
        validation_status="valid",
    )
    extractor._detect_conflicts([cand1, cand2])
    assert cand2.validation_status == "conflicting"
