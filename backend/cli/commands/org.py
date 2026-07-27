import os
import json
import httpx
import typer
from cli.utils.formatting import print_error, print_success, print_info, console, ExitCode

def create_org_command(
    name: str = typer.Option(..., "--name", help="Organization name"),
    slug: str = typer.Option(..., "--slug", help="Organization slug"),
    url: str = typer.Option(os.getenv("ASILA_URL", "http://localhost:8000"), "--url", help="Asila API URL"),
    api_key: str = typer.Option(os.getenv("ASILA_API_KEY"), "--api-key", help="API Key (Owner/Admin)"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Create a new organization."""
    if not api_key:
        print_error("ASILA_MISSING_API_KEY", "API key missing.", "Provide --api-key or ASILA_API_KEY.", "Run 'asila init' first.", exit_code=ExitCode.AUTH_FAILURE)

    try:
        response = httpx.post(
            f"{url.rstrip('/')}/api/v1/organizations",
            headers={"X-Asila-API-Key": api_key},
            json={"name": name, "slug": slug},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if json_output:
            console.print(json.dumps(data, indent=2))
            return
        print_success(f"Organization '{name}' created successfully (ID: {data.get('id')}).")
    except httpx.HTTPError as e:
        print_error("API_ERROR", "Failed to create organization.", str(e), "Check credentials and permissions.", exit_code=ExitCode.INTERNAL_ERROR)
