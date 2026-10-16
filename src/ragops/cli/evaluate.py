"""CLI command for evaluation."""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ragops.core.logging import setup_logging
from ragops.evaluation.runner import EvaluationRunner
from ragops.evaluation.schemas import EvaluationConfig

console = Console()


@click.command(name="evaluate")
@click.option("--dataset", "-d", required=True, help="Path to evaluation dataset (JSONL)")
@click.option("--version", "-v", default="v1", help="RAG version to evaluate")
@click.option("--no-judge", is_flag=True, help="Disable LLM-as-judge evaluation")
@click.option("--output", "-o", default=None, help="Path to save evaluation report JSON")
def evaluate_command(dataset: str, version: str, no_judge: bool, output: str | None):
    """Run evaluation against a golden dataset."""
    setup_logging("INFO")

    console.print(
        Panel.fit(
            f"[bold cyan]RAGOps Evaluation[/bold cyan]\n"
            f"Dataset: {dataset}\nVersion: {version}",
            border_style="cyan",
        )
    )

    config = EvaluationConfig(
        dataset_path=dataset,
        rag_version=version,
        use_llm_judge=not no_judge,
    )

    runner = EvaluationRunner(use_llm_judge=not no_judge)
    result = runner.run(config)

    # Display results
    table = Table(title="Evaluation Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Score", style="green")

    table.add_row("Retrieval Recall@5", f"{result.retrieval_recall:.3f}")
    table.add_row("Retrieval Precision@5", f"{result.retrieval_precision:.3f}")
    table.add_row("MRR", f"{result.mrr:.3f}")
    table.add_row("Faithfulness", f"{result.faithfulness:.3f}")
    table.add_row("Answer Relevance", f"{result.answer_relevance:.3f}")
    table.add_row("Citation Accuracy", f"{result.citation_accuracy:.3f}")
    table.add_row("P50 Latency", f"{result.p50_latency_ms:.0f}ms")
    table.add_row("P95 Latency", f"{result.p95_latency_ms:.0f}ms")
    table.add_row("Samples", str(result.sample_count))

    console.print(table)

    if output:
        import json
        from pathlib import Path
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result.model_dump(), indent=2, default=str), encoding="utf-8")
        console.print(f"✅ Report saved to [bold]{output}[/bold]")


if __name__ == "__main__":
    evaluate_command()
