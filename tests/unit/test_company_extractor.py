"""Tests for dynamic company web extractor, human-in-the-loop approval, and vector store embedding."""

import pytest
from ragops.storage.repositories import CompanyRepository
from ragops.tools.web_extractor import CompanyWebExtractor
from ragops.rag.query_intelligence import QueryIntelligenceEngine


def test_embed_company_profile_and_fetch_locations():
    """Verify company profile embedding and dynamic location retrieval."""
    repo = CompanyRepository()
    profile = repo.get_profile()
    assert profile is not None

    extractor = CompanyWebExtractor()
    count = extractor.embed_company_profile(profile)
    assert count >= 4

    # Query with the user's exact query including spelling typo "loactions"
    results = extractor.fetch_dynamic_web_context("company all loactions")
    assert len(results) > 0
    # The first result should contain locations
    first_text = results[0]["text"]
    assert any(k in first_text.lower() for k in ["pune", "location", "headquarter", "mumbai", "facility"])


def test_query_intelligence_dynamic_locations_intent():
    """Verify QueryIntelligenceEngine detects locations intent even with typos and rewrites dynamically."""
    intel = QueryIntelligenceEngine()

    # User's query with spelling typo
    intent = intel.analyze_and_rewrite("company all loactions")
    assert intent.intent_type == "company_locations"
    assert intent.scope == "company_overview"
    assert intent.is_rewritten is True
    assert "locations" in intent.rewritten_query.lower() or "plants" in intent.rewritten_query.lower()

    # Client query
    client_intent = intel.analyze_and_rewrite("who are company key clients")
    assert client_intent.intent_type == "company_clients"
    assert client_intent.scope == "company_overview"
    assert client_intent.is_rewritten is True
