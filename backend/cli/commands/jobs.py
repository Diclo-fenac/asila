import os
import json
import httpx
import typer
from rich.table import Table
from cli.utils.formatting import print_error, print_success, print_info, console, ExitCode

def get_job_command(
    job_id: str = typer.Argument(..., help="Ingestion Job ID"),
    url: str = typer.Option(os.getenv("ASILA_URL", "http://localhost:8000"), "--url", help="Asila API URL"),
    api_key: str = typer.Option(os.getenv("ASILA_API_KEY"), "--api-key", help="API Key"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Get the status and error details of an ingestion job."""
    if not api_key:
        print_error("ASILA_MISSING_API_KEY", "API key missing.", "Provide --api-key or ASILA_API_KEY.", "Run 'asila init' first.", exit_code=ExitCode.AUTH_FAILURE)

    try:
        response = httpx.get(
            f"{url.rstrip('/')}/api/v1/knowledge/jobs/{job_id}",
            headers={"X-Asila-API-Key": api_key},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if json_output:
            console.print(json.dumps(data, indent=2))
            return

        table = Table(title=f"Job Details: {job_id}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="bold")

        table.add_row("ID", data.get("id", ""))
        table.add_row("Document ID", data.get("document_id", ""))
        table.add_row("Operation", data.get("operation", ""))
        
        status_val = data.get("status", "")
        status_style = "green" if status_val == "completed" else ("red" if status_val == "failed" else "yellow")
        table.add_row("Status", f"[{status_style}]{status_val}[/{status_style}]")
        table.add_row("Attempts", str(data.get("attempts", 0)))
        table.add_row("Last Error", str(data.get("last_error") or "None"))
        table.add_row("Started At", str(data.get("started_at") or "Not started"))
        table.add_row("Completed At", str(data.get("completed_at") or "Not completed"))

        console.print(table)
    except httpx.HTTPError as e:
        print_error("API_ERROR", f"Failed to get job '{job_id}'.", str(e), "Check credentials and scopes.", exit_code=ExitCode.INTERNAL_ERROR)
