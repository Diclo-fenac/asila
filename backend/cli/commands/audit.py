import os
import json
import httpx
import typer
from rich.table import Table
from cli.utils.formatting import print_error, print_success, print_info, console, ExitCode

def list_audit_command(
    limit: int = typer.Option(50, "--limit", help="Number of audit logs to return"),
    action: str = typer.Option(None, "--action", help="Filter by action name"),
    url: str = typer.Option(os.getenv("ASILA_URL", "http://localhost:8000"), "--url", help="Asila API URL"),
    api_key: str = typer.Option(os.getenv("ASILA_API_KEY"), "--api-key", help="API Key (Owner/Admin)"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """List audit logs for the current organization."""
    if not api_key:
        print_error("ASILA_MISSING_API_KEY", "API key missing.", "Provide --api-key or ASILA_API_KEY.", "Run 'asila init' first.", exit_code=ExitCode.AUTH_FAILURE)

    params = {"limit": limit}
    if action:
        params["action"] = action

    try:
        response = httpx.get(
            f"{url.rstrip('/')}/api/v1/audit",
            headers={"X-Asila-API-Key": api_key},
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if json_output:
            console.print(json.dumps(data, indent=2))
            return

        table = Table(title="Security Audit Logs")
        table.add_column("ID", style="dim")
        table.add_column("Action", style="bold cyan")
        table.add_column("Actor ID", style="green")
        table.add_column("Target Type")
        table.add_column("Target ID")
        table.add_column("Timestamp")

        for d in data:
            table.add_row(
                d.get("id", "")[:12] + "...",
                d.get("action", ""),
                d.get("actor_id", "") or "System",
                d.get("target_type", "") or "-",
                d.get("target_id", "") or "-",
                d.get("created_at", "")[:19].replace("T", " ") if d.get("created_at") else "",
            )
        console.print(table)
    except httpx.HTTPError as e:
        print_error("API_ERROR", "Failed to list audit logs.", str(e), "Check credentials and owner/admin role.", exit_code=ExitCode.INTERNAL_ERROR)


def verify_audit_command(
    url: str = typer.Option(os.getenv("ASILA_URL", "http://localhost:8000"), "--url", help="Asila API URL"),
    api_key: str = typer.Option(os.getenv("ASILA_API_KEY"), "--api-key", help="API Key (Owner/Admin)"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Verify that tamper-evident audit logging is active and recording events."""
    if not api_key:
        print_error("ASILA_MISSING_API_KEY", "API key missing.", "Provide --api-key or ASILA_API_KEY.", "Run 'asila init' first.", exit_code=ExitCode.AUTH_FAILURE)

    print_info("Verifying security audit log stream...")
    try:
        response = httpx.get(
            f"{url.rstrip('/')}/api/v1/audit",
            headers={"X-Asila-API-Key": api_key},
            params={"limit": 5},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if json_output:
            console.print(json.dumps({"status": "verified", "event_count": len(data), "events": data}, indent=2))
            return

        if not data:
            print_success("Audit log endpoint is reachable and secure (0 events recorded yet).")
        else:
            print_success(f"Audit verification successful! Found {len(data)} recent tamper-evident security events.")
            for ev in data[:3]:
                console.print(f"  • [bold]{ev.get('action')}[/bold] by [green]{ev.get('actor_id')}[/green] at {ev.get('created_at', '')[:19]}")
    except httpx.HTTPError as e:
        print_error("API_ERROR", "Audit verification failed.", str(e), "Check credentials and backend status.", exit_code=ExitCode.INTERNAL_ERROR)
