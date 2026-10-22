"""CLI command to run API server."""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel
import uvicorn

from ragops.core.logging import setup_logging

console = Console()


@click.command(name="serve")
@click.option("--host", default="0.0.0.0", help="Server host")
@click.option("--port", default=8000, type=int, help="Server port")
@click.option("--reload/--no-reload", default=True, help="Enable auto-reload")
def serve_command(host: str, port: int, reload: bool):
    """Start the RAGOps API server."""
    setup_logging("INFO")

    console.print(
        Panel.fit(
            f"[bold cyan]RAGOps API Server[/bold cyan]\n"
            f"Host: {host}:{port}\n"
            f"Docs: http://{host}:{port}/docs",
            border_style="cyan",
        )
    )

    uvicorn.run(
        "ragops.api.app:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    serve_command()
