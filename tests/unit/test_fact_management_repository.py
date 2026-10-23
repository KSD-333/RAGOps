"""Unit tests for FactManagementRepository, field-level candidate facts, review audit, and transactional outbox."""

import uuid
import pytest
from ragops.storage.repositories import FactManagementRepository


def test_fact_management_lifecycle():
    repo = FactManagementRepository()
    test_org = f"test_org_{uuid.uuid4().hex[:8]}"

    # 1. Register a test company source
    source = repo.register_source(
        display_name="Carraro Test Portal",
        source_url="https://www.carraro.com/test",
        source_type="website",
        country_code="IT",
        organization_id=test_org,
    )
    assert source["display_name"] == "Carraro Test Portal"
    assert source["verification_status"] == "verified"

    # 2. Record source document
    doc = repo.record_source_document(
        content_text="Carraro S.p.A. global headquarters located in Campodarsego, Padua, Italy.",
        canonical_url="https://www.carraro.com/test",
        title="Carraro Test Corporate Profile",
        source_id=source["id"],
        country_code="IT",
        organization_id=test_org,
    )
    assert doc["content_version"] >= 1
    assert len(doc["content_sha256"]) == 64

    # 3. Save candidate with citation evidence
    candidate = repo.save_candidate_with_evidence(
        section_key="identity",
        fact_key="global_headquarters",
        proposed_value="Campodarsego, Padua, Italy",
        scope_key="global",
        document_id=doc["id"],
        validation_status="valid",
        review_status="pending",
        extraction_confidence=0.98,
        organization_id=test_org,
        evidence_list=[
            {
                "evidence_text": "Carraro S.p.A. global headquarters located in Campodarsego, Padua, Italy.",
                "section_heading": "Global Presence",
                "source_url": "https://www.carraro.com/test",
            }
        ],
    )
    assert candidate["section_key"] == "identity"
    assert candidate["fact_key"] == "global_headquarters"
    assert candidate["review_status"] == "pending"
    assert len(candidate["evidence"]) == 1

    # 4. Update candidate proposed value
    updated_cand = repo.update_candidate_proposed_value(
        candidate_id=candidate["id"],
        new_value="Campodarsego (Padua), Italy",
        user_id="test_admin",
    )
    assert updated_cand["proposed_value"] == "Campodarsego (Padua), Italy"

    # 5. Review candidate (Approve) -> atomically creates active fact and outbox event
    review_res = repo.review_candidate(
        candidate_id=candidate["id"],
        decision="approved",
        reviewer_id="test_admin",
        submitted_value="Campodarsego (Padua), Italy",
        reason="Verified against official registered corporate filings",
    )
    assert review_res["decision"] == "approved"
    assert review_res["candidate"]["review_status"] == "approved"
    assert review_res["approved_fact"] is not None
    assert review_res["approved_fact"]["is_active"] is True
    assert review_res["approved_fact"]["version"] == 1

    # 6. Retrieve active approved facts
    approved_facts = repo.get_approved_facts(organization_id=test_org, section_key="identity")
    assert any(f["fact_key"] == "global_headquarters" for f in approved_facts)

    # 7. Check outbox event enqueued
    outbox_events = repo.get_outbox_events(organization_id=test_org, status="pending")
    assert len(outbox_events) >= 1
    job_id = outbox_events[0]["id"]

    # 8. Track ingestion job
    job_status = repo.get_ingestion_job(job_id=job_id, organization_id=test_org)
    assert job_status is not None
    assert job_status["job_id"] == job_id
    assert job_status["status"] == "pending"

    # 9. Process publication outbox
    process_res = repo.process_publication_outbox(organization_id=test_org, limit=10)
    assert process_res["processed"] >= 1

    # 10. Verify job is completed
    job_status_after = repo.get_ingestion_job(job_id=job_id, organization_id=test_org)
    assert job_status_after["status"] == "completed"

    # 11. Cleanup test organization resources
    repo.clear_company_knowledge(organization_id=test_org)
