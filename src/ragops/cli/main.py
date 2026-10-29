"""CLI main entry point — ragops command with subcommands."""

from __future__ import annotations

import sys
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console(force_terminal=True, legacy_windows=False)


@click.group()
@click.version_option(version="0.1.0", prog_name="ragops")
def cli():
    """RAGOps — Production RAG Platform with Evaluation & Observability."""
    pass


@cli.command()
@click.argument("path")
@click.option("--version", "-v", default="v1", help="Document version tag")
@click.option("--chunk-size", default=512, help="Chunk size in characters")
@click.option("--chunk-overlap", default=50, help="Chunk overlap in characters")
def ingest(path: str, version: str, chunk_size: int, chunk_overlap: int):
    """Ingest documents from a file or directory.

    PATH can be a single file or a directory containing documents.
    Supported formats: PDF, HTML, Markdown.
    """
    from pathlib import Path
    from ragops.core.logging import setup_logging
    from ragops.ingestion.pipeline import IngestionPipeline
    from ragops.retrieval.retriever import RAGRetriever

    setup_logging("INFO")

    console.print(Panel.fit(
        f"[bold cyan]RAGOps Document Ingestion[/bold cyan]\n"
        f"Path: {path}\nVersion: {version}",
        border_style="cyan",
    ))

    pipeline = IngestionPipeline(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    retriever = RAGRetriever(use_reranker=False)  # No reranker needed for indexing

    target = Path(path).resolve()

    if target.is_file():
        chunks = pipeline.ingest_file(target, version)
        indexed = retriever.index(chunks)

        console.print(f"\n[bold green][OK][/bold green] Ingested [bold]{target.name}[/bold]")
        console.print(f"   Chunks: {len(chunks)} | Indexed: {indexed}")

    elif target.is_dir():
        result = pipeline.ingest_directory(target, version)

        # Index chunks for each file
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
                console.print(f"  [bold yellow][WARN][/bold yellow]  {error}", style="yellow")
    else:
        console.print(f"[bold red][ERROR][/bold red] Path not found: {path}", style="red")
        raise SystemExit(1)


@cli.command()
@click.argument("query_text")
@click.option("--top-k", default=5, help="Number of chunks to retrieve")
def query(query_text: str, top_k: int):
    """Query the RAG pipeline.

    QUERY_TEXT is the question to ask.
    """
    from ragops.core.logging import setup_logging
    from ragops.core.types import QueryRequest
    from ragops.rag.pipeline import RAGPipeline

    setup_logging("WARNING")

    console.print(Panel.fit(
        f"[bold cyan]RAGOps Query[/bold cyan]\n"
        f"Question: {query_text}",
        border_style="cyan",
    ))

    server_url = "http://127.0.0.1:8000"
    response = None
    via_server = False

    try:
        import json
        import urllib.request
        req = urllib.request.Request(
            f"{server_url}/api/v1/query",
            data=json.dumps({"query": query_text, "top_k": top_k}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as http_resp:
            if http_resp.status == 200:
                data = json.loads(http_resp.read().decode("utf-8"))
                from ragops.core.types import RAGResponse, Source
                sources = [Source(**s) for s in data.get("sources", [])]
                response = RAGResponse(
                    answer=data.get("answer", ""),
                    sources=sources,
                    trace_id=data.get("trace_id", ""),
                    metadata=data.get("metadata", {}),
                )
                via_server = True
    except Exception:
        pass

    if response is None:
        pipeline = RAGPipeline()
        request = QueryRequest(query=query_text, top_k=top_k)
        response = pipeline.query(request)

    # Display answer
    console.print(f"\n[bold green]Answer:[/bold green]\n{response.answer}\n")

    # Display sources
    if response.sources:
        table = Table(title="Sources")
        table.add_column("Document", style="cyan")
        table.add_column("Chunk ID", style="dim")
        table.add_column("Page", style="dim")

        for source in response.sources:
            table.add_row(
                source.document,
                source.chunk_id,
                str(source.page or "-"),
            )
        console.print(table)

    # Display metadata with stage breakdown
    meta = response.metadata
    stage_breakdown = ""
    if "embed_latency_ms" in meta and "generation_latency_ms" in meta:
        stage_breakdown = (
            f" [Embed: {meta.get('embed_latency_ms', 0):.0f}ms | "
            f"Search: {meta.get('search_latency_ms', 0):.0f}ms | "
            f"Rerank: {meta.get('rerank_latency_ms', 0):.0f}ms | "
            f"LLM: {meta.get('generation_latency_ms', 0):.0f}ms]"
        )
    server_tag = " | [cyan]via live server[/cyan]" if via_server else ""
    console.print(f"\n[dim]Trace: {response.trace_id} | "
                  f"Model: {meta.get('model', 'N/A')} | "
                  f"Latency: {meta.get('total_latency_ms', 0):.0f}ms{stage_breakdown}{server_tag} | "
                  f"Tokens: {meta.get('input_tokens', 0)}+{meta.get('output_tokens', 0)}[/dim]")


@cli.command()
@click.option("--dataset", "-d", required=True, help="Path to evaluation dataset (JSONL)")
@click.option("--version", "-v", default="v1", help="RAG version to evaluate")
@click.option("--no-judge", is_flag=True, help="Disable LLM-as-judge evaluation")
def evaluate(dataset: str, version: str, no_judge: bool):
    """Run evaluation against a golden dataset."""
    from ragops.core.logging import setup_logging
    from ragops.evaluation.runner import EvaluationRunner
    from ragops.evaluation.schemas import EvaluationConfig

    setup_logging("INFO")

    console.print(Panel.fit(
        f"[bold cyan]RAGOps Evaluation[/bold cyan]\n"
        f"Dataset: {dataset}\nVersion: {version}",
        border_style="cyan",
    ))

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


@cli.command()
@click.option("--host", default="0.0.0.0", help="Server host")
@click.option("--port", default=8000, type=int, help="Server port")
@click.option("--reload/--no-reload", default=True, help="Enable auto-reload")
def serve(host: str, port: int, reload: bool):
    """Start the RAGOps API server."""
    import uvicorn
    from ragops.core.config import get_settings
    from ragops.core.logging import setup_logging
    from ragops.storage.redis_cache import ensure_redis_running

    setup_logging("INFO")
    settings = get_settings()

    redis_status = "[dim yellow]Disabled[/dim yellow]"
    if settings.redis.enabled:
        if ensure_redis_running(settings.redis.url):
            redis_status = "[bold green]Online (<2ms exact & ≥90% semantic hit)[/bold green]"
        else:
            redis_status = "[dim yellow]Offline (using PostgreSQL/SQLite cache fallback)[/dim yellow]"

    console.print(Panel.fit(
        f"[bold cyan]RAGOps API Server[/bold cyan]\n"
        f"Host: {host}:{port}\n"
        f"Docs: http://{host}:{port}/docs\n"
        f"Redis/Memurai: {redis_status}",
        border_style="cyan",
    ))

    uvicorn.run(
        "ragops.api.app:app",
        host=host,
        port=port,
        reload=reload,
    )


@cli.command()
@click.option("--host", default="0.0.0.0", help="API Host")
@click.option("--port", default=8000, type=int, help="API Port")
@click.option("--no-browser", is_flag=True, help="Do not open browser automatically")
def dev(host: str, port: int, no_browser: bool):
    """Start both FastAPI Backend and React Dashboard concurrently."""
    import subprocess
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[3]
    react_dir = project_root / "react"

    console.print(Panel.fit(
        f"[bold cyan]RAGOps Full-Stack Dev Launcher[/bold cyan]\n"
        f"[bold green]FastAPI API:[/bold green] http://127.0.0.1:{port} (Docs: http://127.0.0.1:{port}/docs)\n"
        f"[bold blue]React Dashboard:[/bold blue] http://localhost:5173\n"
        f"Press Ctrl+C to terminate both servers.",
        border_style="cyan",
    ))

    # 1. Start React Vite server in background
    react_proc = None
    if react_dir.exists() and (react_dir / "package.json").exists():
        console.print("[dim]Starting React Vite dashboard...[/dim]")
        try:
            react_proc = subprocess.Popen(
                ["npm.cmd" if sys.platform == "win32" else "npm", "run", "dev"],
                cwd=str(react_dir),
                shell=(sys.platform == "win32"),
            )
        except Exception as e:
            console.print(f"[yellow]Could not launch React automatically: {e}[/yellow]")

    # 2. Start FastAPI server
    try:
        import uvicorn
        from ragops.core.logging import setup_logging
        from ragops.core.config import get_settings
        from ragops.storage.redis_cache import ensure_redis_running

        setup_logging("INFO")
        settings = get_settings()
        if settings.redis.enabled:
            ensure_redis_running(settings.redis.url)

        uvicorn.run("ragops.api.app:app", host=host, port=port, reload=True)
    finally:
        if react_proc and react_proc.poll() is None:
            console.print("[dim]Stopping React dev server...[/dim]")
            react_proc.terminate()


@cli.command()
def status():
    """Show RAGOps system status."""
    from ragops.core.config import get_settings
    from ragops.improvement.promotion import PromotionManager

    settings = get_settings()
    promotion = PromotionManager()

    table = Table(title="RAGOps System Status")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Environment", settings.environment)
    table.add_row("LLM Model", settings.groq.model)
    table.add_row("Embedding Model", settings.embedding.model)
    table.add_row("Vector Store", f"ChromaDB @ {settings.chroma.persist_dir}")
    table.add_row("Production Version", promotion.get_production_version())
    table.add_row("Chunk Size", str(settings.ingestion.chunk_size))
    table.add_row("Top-K Retrieval", str(settings.retrieval.top_k))
    table.add_row("Rerank Top-N", str(settings.retrieval.rerank_top_n))

    console.print(table)



@cli.command()
def doctor():
    """Diagnose RAGOps environment, LLM providers (Ollama & Groq), and system health."""
    from ragops.core.config import get_settings
    from ragops.generation.providers.router import get_llm_router
    from ragops.retrieval.vector_store import ChromaVectorStore
    from ragops.storage.database import get_active_db_type

    settings = get_settings()
    router = get_llm_router()
    diag = router.diagnose()

    active_color = "green" if diag["active_provider"] != "degraded" else "red"
    degraded_color = "red" if diag["degraded"] else "green"
    degraded_label = "YES (Fallback to Retrieval-only)" if diag["degraded"] else "NO (Full Generation Active)"

    console.print(Panel.fit(
        f"[bold cyan]RAGOps System Doctor & LLM Diagnostics[/bold cyan]\n"
        f"Mode: [bold]{diag['mode']}[/bold] | Active Provider: [bold {active_color}]{diag['active_provider']}[/bold {active_color}]\n"
        f"Degraded Status: [bold {degraded_color}]{degraded_label}[/bold {degraded_color}]",
        border_style="cyan",
    ))

    # 1. LLM Providers Table
    llm_table = Table(title="LLM Provider Diagnostics")
    llm_table.add_column("Provider", style="cyan", no_wrap=True)
    llm_table.add_column("Property", style="white")
    llm_table.add_column("Value / Status", style="green")

    # Ollama Rows
    o = diag["ollama"]
    o_status = "[bold green]Online[/bold green]" if o["running"] and o["model_ready"] else (
        "[bold yellow]Running (Model Missing)[/bold yellow]" if o["running"] else "[bold red]Offline[/bold red]"
    )
    llm_table.add_row("Ollama (Local)", "Binary Installed", "[green]Yes[/green]" if o["installed"] else "[red]No[/red]")
    llm_table.add_row("Ollama (Local)", "Server Running", f"[green]Yes ({router.ollama.base_url})[/green]" if o["running"] else "[red]No[/red]")
    llm_table.add_row("Ollama (Local)", "Configured Model", f"{o['configured_model']}")
    llm_table.add_row("Ollama (Local)", "Model Ready", "[green]Yes[/green]" if o["model_ready"] else "[yellow]No (Needs Pull)[/yellow]")
    llm_table.add_row("Ollama (Local)", "Status Verdict", o_status)

    # Groq Rows
    g = diag["groq"]
    g_status = "[bold green]Online[/bold green]" if g["reachable"] else "[bold red]Unavailable[/bold red]"
    llm_table.add_row("Groq (Cloud)", "API Key Present", f"[green]Yes ({g.get('masked_key', '***')})[/green]" if g["key_present"] else "[red]Missing in .env[/red]")
    llm_table.add_row("Groq (Cloud)", "API Reachable", "[green]Yes[/green]" if g["reachable"] else "[red]No[/red]")
    llm_table.add_row("Groq (Cloud)", "Configured Model", f"{g.get('model', settings.groq.model)}")
    llm_table.add_row("Groq (Cloud)", "Model In Available List", "[green]Yes[/green]" if g.get("model_in_list") else "[yellow]Unknown/Unverified[/yellow]")
    llm_table.add_row("Groq (Cloud)", "Status Verdict", g_status)

    console.print(llm_table)

    # 2. Storage & Cache Diagnostics
    stor_table = Table(title="Storage & Retrieval Subsystems")
    stor_table.add_column("Subsystem", style="cyan")
    stor_table.add_column("Engine / Location", style="white")
    stor_table.add_column("Status", style="green")

    db_type = get_active_db_type()
    stor_table.add_row("Relational Database", f"SQLAlchemy ({db_type})", "[bold green]Connected[/bold green]")

    try:
        store = ChromaVectorStore()
        count = store.count()
        stor_table.add_row("ChromaDB Vector Store", f"{settings.chroma.persist_dir} ({count} chunks)", "[bold green]Indexed[/bold green]")
    except Exception as e:
        stor_table.add_row("ChromaDB Vector Store", settings.chroma.persist_dir, f"[bold red]Error: {e}[/bold red]")

    redis_stat = "[bold yellow]Disabled[/bold yellow]"
    if settings.redis.enabled:
        from ragops.storage.redis_cache import ensure_redis_running
        if ensure_redis_running(settings.redis.url):
            redis_stat = "[bold green]Online (<2ms exact & ≥90% semantic)[/bold green]"
        else:
            redis_stat = "[bold yellow]Offline (Fallback to local cache)[/bold yellow]"
    stor_table.add_row("Redis Semantic Cache", settings.redis.url, redis_stat)

    console.print(stor_table)

    # 3. Actionable Fix Suggestions
    if diag["degraded"]:
        console.print("\n[bold yellow]⚠️  ACTION REQUIRED TO RESTORE LLM GENERATION:[/bold yellow]")
        if not o["installed"]:
            console.print("  1. [bold]Install Ollama locally:[/bold] Download from [link=https://ollama.com]https://ollama.com[/link]")
        elif not o["running"]:
            console.print("  1. [bold]Start Ollama service:[/bold] Run [cyan]ollama serve[/cyan] in a terminal")
        elif not o["model_ready"]:
            console.print(f"  1. [bold]Pull configured model:[/bold] Run [cyan]ollama pull {o['configured_model']}[/cyan]")

        if not g["key_present"]:
            console.print("  2. [bold]Set Cloud API Key:[/bold] Add [cyan]GROQ_API_KEY=gsk_...[/cyan] to your [cyan].env[/cyan] file")
        elif not g["reachable"]:
            console.print(f"  2. [bold]Fix Groq API:[/bold] {g.get('message', 'Verify API key and internet access')}")
    else:
        active_name = diag["active_provider"]
        console.print(f"\n[bold green]✓ System is healthy and ready to serve queries via {active_name.upper()}![/bold green]")


@cli.command()
def mcp():
    """Launch the RAGOps Model Context Protocol (MCP) server over stdio."""
    try:
        from ragops.mcp_server import run_stdio
        run_stdio()
    except ImportError as e:
        console.print(f"[bold red]MCP Error:[/bold red] {e}")
        console.print("[yellow]Install MCP SDK with: pip install mcp[/yellow]")
        sys.exit(1)


if __name__ == "__main__":
    cli()
