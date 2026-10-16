"""CLI command for document ingestion."""

from __future__ import annotations

from pathlib import Path
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ragops.core.logging import setup_logging
from ragops.ingestion.pipeline import IngestionPipeline
from ragops.retrieval.retriever import RAGRetriever

console = Console()


@click.command(name="ingest")
@click.argument("path")
@click.option("--version", "-v", default="v1", help="Document version tag")
@click.option("--chunk-size", default=512, help="Chunk size in characters")
@click.option("--chunk-overlap", default=50, help="Chunk overlap in characters")
def ingest_command(path: str, version: str, chunk_size: int, chunk_overlap: int):
    """Ingest documents from a file or directory.

    PATH can be a single file or a directory containing documents.
    Supported formats: PDF, HTML, Markdown.
    """
    setup_logging("INFO")

    console.print(
        Panel.fit(
            f"[bold cyan]RAGOps Document Ingestion[/bold cyan]\n"
            f"Path: {path}\nVersion: {version}",
            border_style="cyan",
        )
    )

    pipeline = IngestionPipeline(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    retriever = RAGRetriever(use_reranker=False)

    target = Path(path).resolve()

    if target.is_file():
        chunks = pipeline.ingest_file(target, version)
        indexed = retriever.index(chunks)

        console.print(f"\n✅ Ingested [bold]{target.name}[/bold]")
        console.print(f"   Chunks: {len(chunks)} | Indexed: {indexed}")

    elif target.is_dir():
        result = pipeline.ingest_directory(target, version)

        total_indexed = 0
        supported = {".pdf", ".html", ".htm", ".md", ".markdown"}
        for file_path in sorted(target.rglob("*")):
            if file_path.suffix.lower() in supported:
                try:
                    chunks = pipeline.ingest_file(file_path, version)
                    total_indexed += retriever.index(chunks)
                except Exception:
                    continue

        table = Table(title="Ingestion Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Documents Processed", str(result.documents_processed))
        table.add_row("Chunks Created", str(result.chunks_created))
        table.add_row("Chunks Indexed", str(total_indexed))
        table.add_row("Errors", str(len(result.errors)))

        console.print(table)

        if result.errors:
            for error in result.errors:
                console.print(f"  ⚠️  {error}", style="yellow")
    else:
        console.print(f"❌ Path not found: {path}", style="red")
        raise SystemExit(1)


if __name__ == "__main__":
    ingest_command()
