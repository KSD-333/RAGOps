"""Evaluation schemas — models specific to the evaluation module."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvaluationConfig(BaseModel):
    """Configuration for an evaluation run."""
    dataset_path: str
    rag_version: str = "v1"
    top_k: int = 10
    use_llm_judge: bool = True
    save_report: bool = True
    report_dir: str = "evaluation/reports"
