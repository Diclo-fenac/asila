import os
import json
import httpx
import typer
from rich.table import Table
from cli.utils.formatting import print_error, print_success, print_info, console, ExitCode

def create_key_command(
    name: str = typer.Option(..., "--name", help="Key name"),
    scopes: str = typer.Option("knowledge:read,knowledge:search", "--scopes", help="Comma-separated scopes"),
    org_id: str = typer.Option(os.getenv("ASILA_ORG_ID"), "--org-id", help="Organization ID"),
    url: str = typer.Option(os.getenv("ASILA_URL", "http://localhost:8000"), "--url", help="Asila API URL"),
    api_key: str = typer.Option(os.getenv("ASILA_API_KEY"), "--api-key", help="API Key (Owner/Admin)"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Create a new API key."""
    if not api_key:
        print_error("ASILA_MISSING_API_KEY", "API key missing.", "Provide --api-key or ASILA_API_KEY.", "Run 'asila init' first.", exit_code=ExitCode.AUTH_FAILURE)

    scope_list = [s.strip() for s in scopes.split(",") if s.strip()]
    headers = {"X-Asila-API-Key": api_key}
    if org_id:
        headers["X-Organization-Id"] = org_id

    try:
        response = httpx.post(
            f"{url.rstrip('/')}/api/v1/api-keys",
            headers=headers,
            json={"name": name, "scopes": scope_list},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if json_output:
            console.print(json.dumps(data, indent=2))
            return
        print_success(f"API Key '{name}' created successfully.")
        console.print(f"[bold green]Secret:[/bold green] {data.get('api_key')}")
        console.print("[dim]Save this secret now. It will never be shown again.[/dim]")
    except httpx.HTTPError as e:
        print_error("API_ERROR", "Failed to create API key.", str(e), "Check credentials and org ID.", exit_code=ExitCode.INTERNAL_ERROR)


def list_keys_command(
    org_id: str = typer.Option(os.getenv("ASILA_ORG_ID"), "--org-id", help="Organization ID"),
    url: str = typer.Option(os.getenv("ASILA_URL", "http://localhost:8000"), "--url", help="Asila API URL"),
    api_key: str = typer.Option(os.getenv("ASILA_API_KEY"), "--api-key", help="API Key (Owner/Admin)"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """List API keys for an organization."""
    if not api_key:
        print_error("ASILA_MISSING_API_KEY", "API key missing.", "Provide --api-key or ASILA_API_KEY.", "Run 'asila init' first.", exit_code=ExitCode.AUTH_FAILURE)

    headers = {"X-Asila-API-Key": api_key}
    if org_id:
        headers["X-Organization-Id"] = org_id

    try:
        response = httpx.get(
            f"{url.rstrip('/')}/api/v1/api-keys",
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if json_output:
            console.print(json.dumps(data, indent=2))
            return

        table = Table(title="API Keys")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="bold")
        table.add_column("Prefix")
        table.add_column("Scopes")
        table.add_column("Status")

        for k in data:
            status_str = "[red]Revoked[/red]" if k.get("revoked_at") else "[green]Active[/green]"
            table.add_row(k.get("id", ""), k.get("name", ""), k.get("key_prefix", ""), ", ".join(k.get("scopes", [])), status_str)
        console.print(table)
    except httpx.HTTPError as e:
        print_error("API_ERROR", "Failed to list API keys.", str(e), "Check credentials and org ID.", exit_code=ExitCode.INTERNAL_ERROR)


def revoke_key_command(
    key_id: str = typer.Argument(..., help="API Key ID to revoke"),
    org_id: str = typer.Option(os.getenv("ASILA_ORG_ID"), "--org-id", help="Organization ID"),
    url: str = typer.Option(os.getenv("ASILA_URL", "http://localhost:8000"), "--url", help="Asila API URL"),
    api_key: str = typer.Option(os.getenv("ASILA_API_KEY"), "--api-key", help="API Key (Owner/Admin)"),
):
    """Revoke an API key."""
    if not api_key:
        print_error("ASILA_MISSING_API_KEY", "API key missing.", "Provide --api-key or ASILA_API_KEY.", "Run 'asila init' first.", exit_code=ExitCode.AUTH_FAILURE)

    headers = {"X-Asila-API-Key": api_key}
    if org_id:
        headers["X-Organization-Id"] = org_id

    try:
        response = httpx.delete(
            f"{url.rstrip('/')}/api/v1/api-keys/{key_id}",
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        print_success(f"API Key '{key_id}' revoked successfully.")
    except httpx.HTTPError as e:
        print_error("API_ERROR", f"Failed to revoke key '{key_id}'.", str(e), "Check credentials and org ID.", exit_code=ExitCode.INTERNAL_ERROR)


def rotate_key_command(
    key_id: str = typer.Argument(..., help="Old API Key ID to rotate"),
    name: str = typer.Option(None, "--name", help="New Key Name (defaults to 'Rotated from <old_id>')"),
    scopes: str = typer.Option("knowledge:read,knowledge:search", "--scopes", help="Comma-separated scopes for new key"),
    org_id: str = typer.Option(os.getenv("ASILA_ORG_ID"), "--org-id", help="Organization ID"),
    url: str = typer.Option(os.getenv("ASILA_URL", "http://localhost:8000"), "--url", help="Asila API URL"),
    api_key: str = typer.Option(os.getenv("ASILA_API_KEY"), "--api-key", help="API Key (Owner/Admin)"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Rotate an API key by creating a replacement and revoking the old key."""
    if not api_key:
        print_error("ASILA_MISSING_API_KEY", "API key missing.", "Provide --api-key or ASILA_API_KEY.", "Run 'asila init' first.", exit_code=ExitCode.AUTH_FAILURE)

    new_name = name or f"Rotated-{key_id[:8]}"
    print_info(f"Step 1/2: Creating replacement key '{new_name}'...")
    create_key_command(name=new_name, scopes=scopes, org_id=org_id, url=url, api_key=api_key, json_output=json_output)
    print_info(f"Step 2/2: Revoking old key '{key_id}'...")
    revoke_key_command(key_id=key_id, org_id=org_id, url=url, api_key=api_key)
    print_success("Key rotation completed securely.")
