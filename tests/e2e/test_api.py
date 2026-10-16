"""E2E tests for RAGOps FastAPI application endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_health_endpoint(api_client: TestClient) -> None:
    response = api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ragops"


def test_readiness_endpoint(api_client: TestClient) -> None:
    response = api_client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "environment" in data


def test_metrics_endpoint(api_client: TestClient) -> None:
    response = api_client.get("/metrics")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


def test_feedback_flow(api_client: TestClient) -> None:
    payload = {
        "trace_id": "test_trace_12345",
        "rating": "positive",
        "comment": "Accurate response with valid citations.",
    }
    response = api_client.post("/api/v1/feedback", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "recorded"
    assert data["feedback_id"].startswith("fb_")


    # Check stats endpoint
    stats_response = api_client.get("/api/v1/feedback/stats")
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert stats["total"] >= 1
    assert stats["positive"] >= 1


def test_document_count_endpoint(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/documents/count")
    assert response.status_code == 200
    assert "count" in response.json()
