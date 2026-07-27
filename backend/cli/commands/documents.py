import os
import json
import httpx
import typer
from rich.table import Table
from cli.utils.formatting import print_error, print_success, print_info, console, ExitCode

def list_docs_command(
    limit: int = typer.Option(50, "--limit", help="Number of documents to return"),
    url: str = typer.Option(os.getenv("ASILA_URL", "http://localhost:8000"), "--url", help="Asila API URL"),
    api_key: str = typer.Option(os.getenv("ASILA_API_KEY"), "--api-key", help="API Key"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """List indexed documents."""
    if not api_key:
        print_error("ASILA_MISSING_API_KEY", "API key missing.", "Provide --api-key or ASILA_API_KEY.", "Run 'asila init' first.", exit_code=ExitCode.AUTH_FAILURE)

    try:
        response = httpx.get(
            f"{url.rstrip('/')}/api/v1/knowledge/documents",
            headers={"X-Asila-API-Key": api_key},
            params={"limit": limit},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if json_output:
            console.print(json.dumps(data, indent=2))
            return

        table = Table(title="Knowledge Documents")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="bold")
        table.add_column("Source URI")
        table.add_column("Status")
        table.add_column("Created At")

        for d in data:
            status_style = "green" if d.get("status") == "ready" else "yellow"
            table.add_row(
                d.get("id", ""),
                d.get("title", ""),
                d.get("source_uri", ""),
                f"[{status_style}]{d.get('status', '')}[/{status_style}]",
                d.get("created_at", "")[:19].replace("T", " ") if d.get("created_at") else "",
            )
        console.print(table)
    except httpx.HTTPError as e:
        print_error("API_ERROR", "Failed to list documents.", str(e), "Check credentials and scopes.", exit_code=ExitCode.INTERNAL_ERROR)


def delete_doc_command(
    document_id: str = typer.Argument(..., help="Document ID to delete"),
    url: str = typer.Option(os.getenv("ASILA_URL", "http://localhost:8000"), "--url", help="Asila API URL"),
    api_key: str = typer.Option(os.getenv("ASILA_API_KEY"), "--api-key", help="API Key"),
):
    """Delete an indexed document."""
    if not api_key:
        print_error("ASILA_MISSING_API_KEY", "API key missing.", "Provide --api-key or ASILA_API_KEY.", "Run 'asila init' first.", exit_code=ExitCode.AUTH_FAILURE)

    try:
        response = httpx.delete(
            f"{url.rstrip('/')}/api/v1/knowledge/documents/{document_id}",
            headers={"X-Asila-API-Key": api_key},
            timeout=10,
        )
        response.raise_for_status()
        print_success(f"Document '{document_id}' deleted successfully.")
    except httpx.HTTPError as e:
        print_error("API_ERROR", f"Failed to delete document '{document_id}'.", str(e), "Check credentials and scopes.", exit_code=ExitCode.INTERNAL_ERROR)
