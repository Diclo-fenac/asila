import os
import httpx
import typer
from rich.table import Table
from rich.console import Console
from cli.utils.formatting import print_error, print_success, print_info, console, ExitCode

def doctor_command(
    url: str = typer.Option(os.getenv("ASILA_URL", "http://localhost:8000"), "--url", help="Asila API URL"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON")
):
    """Check Asila dependencies and stack health."""
    
    if not json_output:
        print_info("Running health checks...")

    try:
        response = httpx.get(f"{url.rstrip('/')}/api/v1/health/ready", timeout=5)
        is_healthy = response.status_code == 200
        data = response.json() if response.status_code in (200, 503) else {}
        
        if json_output:
            typer.echo(response.text)
            return

        table = Table(title="Asila Stack Health")
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Details")
        
        # We assume the health endpoint returns something like:
        # {"status": "ok", "checks": {"postgres": "ok", "ollama": "ok", "docling": "error"}}
        checks = data.get("checks", {})
        
        def get_status_style(status_str: str) -> str:
            if status_str == "ok": return "[green]OK[/green]"
            if status_str == "error": return "[red]ERROR[/red]"
            return f"[yellow]{status_str}[/yellow]"
            
        if not checks:
            table.add_row("API", get_status_style("error" if not is_healthy else "ok"), f"HTTP {response.status_code}")
        else:
            table.add_row("API", get_status_style(data.get("status", "error")), "Core Backend")
            for service, status in checks.items():
                table.add_row(service.capitalize(), get_status_style(status), "")
                
        console.print(table)
        
        if is_healthy:
            print_success("Stack is healthy and ready to serve.")
        else:
            print_error(
                "ASILA_DEPENDENCY_FAILURE",
                "One or more dependencies are offline.",
                "The health check endpoint reported failure.",
                "Check Docker logs:\n  docker compose logs",
                exit_code=ExitCode.DEPENDENCY_UNAVAILABLE
            )

    except httpx.ConnectError:
        if json_output:
            typer.echo('{"status":"error","message":"API unreachable"}')
            raise typer.Exit(ExitCode.DEPENDENCY_UNAVAILABLE)
            
        print_error(
            "ASILA_API_UNAVAILABLE",
            "API cannot be reached.",
            f"Failed to connect to {url}/api/v1/health/ready",
            "Start the stack:\n  docker compose up -d",
            exit_code=ExitCode.DEPENDENCY_UNAVAILABLE
        )
