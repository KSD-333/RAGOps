"""Integration test for querying locations through RAG pipeline."""

import pytest
from ragops.rag.pipeline import RAGPipeline
from ragops.core.types import QueryRequest
from ragops.storage.repositories import CompanyRepository
from ragops.tools.web_extractor import CompanyWebExtractor


def test_rag_pipeline_answers_company_locations_query():
    # Test using a fictitious entity and clean up afterwards
    repo = CompanyRepository()
    try:
        repo.update_profile({
            "company_name": "TestCorp International",
            "group_name": "TestCorp Group",
            "locations": [
                {"city": "Metropolis", "state": "Central", "type": "Manufacturing Plant", "address": "123 Industrial Way"},
                {"city": "Capital City", "state": "North", "type": "Global Headquarters", "address": "1 Global Plaza"},
            ],
        })
        profile = repo.get_profile()
        extractor = CompanyWebExtractor()
        extractor.embed_company_profile(profile)

        pipeline = RAGPipeline()
        response = pipeline.query(QueryRequest(query="company all locations"))

        ans = response.answer.lower()
        # It must NOT say ungrounded rejection
        assert "i'm sorry, but the provided documents do not contain" not in ans
        assert any(w in ans for w in ["metropolis", "capital", "plant", "location", "headquarters"])
    finally:
        # Guarantee database remains clean and unpolluted
        repo.update_profile({
            "company_name": "",
            "group_name": "",
            "industry": "",
            "locations": [],
            "products": [],
            "directors": [],
            "ceo": "",
            "domains_urls": [],
            "metadata_json": {},
        })
