#!/usr/bin/env python3
"""Script to initialize database tables and seed baseline metrics and sample records."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import uuid

# Ensure src is on sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "src"))

from ragops.core.logging import setup_logging, get_logger
from ragops.storage.database import init_db, get_session
from ragops.storage.models import DocumentModel, EvaluationModel, FeedbackModel, TraceModel
from ragops.improvement.promotion import PromotionManager

logger = get_logger(__name__)


def seed():
    setup_logging("INFO")
    logger.info("initializing_database")
    init_db()

    session = get_session()
    try:
        # Check if already seeded
        existing_eval = session.query(EvaluationModel).first()
        if existing_eval is None:
            logger.info("seeding_baseline_evaluation")
            baseline_eval = EvaluationModel(
                dataset_version="golden_v1",
                rag_version="v1.0.0",
                retrieval_recall=0.88,
                faithfulness=0.92,
                answer_relevance=0.89,
                citation_accuracy=0.95,
                p95_latency_ms=1850.0,
                total_input_tokens=1240,
                total_output_tokens=350,
                sample_count=5,
                evaluated_at=datetime.now(timezone.utc),
            )
            session.add(baseline_eval)

        # Seed sample documents metadata
        existing_doc = session.query(DocumentModel).first()
        if existing_doc is None:
            logger.info("seeding_sample_document_metadata")
            doc1 = DocumentModel(
                document_id="doc_arch_001",
                source="data/raw/architecture_guide.md",
                version="v1",
                chunk_count=6,
                metadata_json={"author": "Architecture Team", "category": "system_design"},
            )
            doc2 = DocumentModel(
                document_id="doc_sec_002",
                source="data/raw/security_handbook.md",
                version="v1",
                chunk_count=4,
                metadata_json={"author": "Security Team", "category": "governance"},
            )
            session.add_all([doc1, doc2])

        # Seed sample trace and feedback
        existing_trace = session.query(TraceModel).first()
        if existing_trace is None:
            logger.info("seeding_sample_trace_and_feedback")
            seed_trace_id = f"trace_{uuid.uuid4().hex[:12]}"
            trace = TraceModel(
                trace_id=seed_trace_id,
                query="What embedding model is used by default in RAGOps?",
                answer="RAGOps uses sentence-transformers all-MiniLM-L6-v2 with 384 dimensions by default.",
                model="llama-3.1-70b-versatile",
                input_tokens=142,
                output_tokens=28,
                retrieval_latency_ms=64.2,
                generation_latency_ms=750.5,
                total_latency_ms=814.7,
                chunks_retrieved=5,
            )
            session.add(trace)

            feedback = FeedbackModel(
                feedback_id=f"fb_{uuid.uuid4().hex[:10]}",
                trace_id=seed_trace_id,
                rating="positive",
                comment="Accurate answer with valid citation.",
            )
            session.add(feedback)

        session.commit()
        logger.info("database_seeded_successfully")

        # Initialize promotion record
        from ragops.core.types import PromotionDecision, PromotionStatus
        promotion = PromotionManager()
        decision = PromotionDecision(
            status=PromotionStatus.PASS,
            candidate_version="v1.0.0",
            production_version="v0.0.0",
            reasons=["Baseline production release with verified golden benchmarks"],
        )
        promotion.promote(decision)
        logger.info("production_version_registered", version="v1.0.0")


    except Exception as e:
        session.rollback()
        logger.error("seeding_failed", error=str(e))
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed()
