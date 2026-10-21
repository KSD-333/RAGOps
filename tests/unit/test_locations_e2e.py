"""Integration test for querying locations through RAG pipeline."""

import pytest
from ragops.rag.pipeline import RAGPipeline
from ragops.core.types import QueryRequest
from ragops.storage.repositories import CompanyRepository
from ragops.tools.web_extractor import CompanyWebExtractor


def test_rag_pipeline_answers_company_locations_query():
    # Ensure profile is embedded
    repo = CompanyRepository()
    profile = repo.get_profile()
    extractor = CompanyWebExtractor()
    extractor.embed_company_profile(profile)

    pipeline = RAGPipeline()
    response = pipeline.query(QueryRequest(query="company all loactions"))

    ans = response.answer.lower()
    # It must NOT say "I'm sorry, but the provided documents do not contain any information"
    assert "i'm sorry, but the provided documents do not contain" not in ans
    # It should mention Pune or Ranjangaon or Italy or locations
    assert any(w in ans for w in ["pune", "ranjangaon", "italy", "campodarsego", "plant", "location", "headquarters"])
