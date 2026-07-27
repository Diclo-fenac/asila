import os
import shutil
import secrets
import httpx
import typer
from pathlib import Path
from cli.utils.formatting import print_success, print_error, print_info, console, ExitCode

def generate_token() -> str:
    return secrets.token_hex(32)

def init_command(
    url: str = typer.Option(os.getenv("ASILA_URL", "http://localhost:8000"), "--url", help="Asila API URL"),
    org: str = typer.Option(None, "--org", help="Organization name"),
    project: str = typer.Option(None, "--project", help="Project name"),
    force: bool = typer.Option(False, "--force", "-f", help="Force initialization"),
    non_interactive: bool = typer.Option(False, "--non-interactive", help="Skip interactive prompts")
):
    """Initialize a local Asila deployment."""
    env_path = Path(".env")
    env_example = Path(".env.example")
    
    # Phase 1: Local bootstrap if .env doesn't exist
    if not env_path.exists():
        print_info("No .env file found. Starting local bootstrap...")
        
        if not env_example.exists():
            print_error(
                "ASILA_MISSING_ENV_EXAMPLE",
                ".env.example file not found.",
                "The CLI cannot generate a .env file because .env.example is missing from the current directory.",
                "Ensure you are in the Asila repository root.",
                exit_code=ExitCode.CONFIG_FAILURE
            )
            
        if not non_interactive and not force:
            confirm = typer.confirm("Create .env from .env.example?")
            if not confirm:
                raise typer.Abort()
                
        # Generate tokens
        master_key = generate_token()
        setup_token = generate_token()
        
        with open(env_example, "r") as f:
            content = f.read()
            
        content = content.replace("ASILA_MASTER_KEY=", f"ASILA_MASTER_KEY={master_key}")
        content = content.replace("ASILA_SETUP_TOKEN=", f"ASILA_SETUP_TOKEN={setup_token}")
        content = content.replace("POSTGRES_PASSWORD=", f"POSTGRES_PASSWORD={generate_token()}")
        
        with open(env_path, "w") as f:
            f.write(content)
            
        print_success(".env file created and populated with secure development secrets.")
        print_info("\nNext steps:")
        console.print("  1. Review [bold].env[/bold] to customize your setup (optional)")
        console.print("  2. Start the Asila stack: [bold]docker compose up -d[/bold]")
        console.print("  3. Run [bold]asila doctor[/bold] to verify health")
        console.print("  4. Run [bold]asila init[/bold] again to provision your organization")
        return

    # Phase 2: Organization provisioning
    setup_token = os.getenv("ASILA_SETUP_TOKEN")
    if not setup_token:
        print_error(
            "ASILA_MISSING_SETUP_TOKEN",
            "Setup token missing.",
            "The ASILA_SETUP_TOKEN is not defined in your environment.",
            "Check your .env file and ensure it is exported, or re-run init.",
            exit_code=ExitCode.CONFIG_FAILURE
        )
        
    print_info("Provisioning Asila Organization...")
    
    if not org and not non_interactive:
        org = typer.prompt("Organization Name", default="My Asila Organization")
    elif not org:
        org = "My Asila Organization"
        
    org_slug = org.lower().replace(" ", "-")

    try:
        response = httpx.post(
            f"{url.rstrip('/')}/api/v1/setup",
            headers={"X-Asila-Setup-Token": setup_token},
            json={
                "owner_email": "admin@local.host",
                "owner_name": "Local Admin",
                "organization_name": org,
                "organization_slug": org_slug,
            },
            timeout=10,
        )
        
        if response.status_code == 400 and "already initialized" in response.text.lower():
            print_success("Organization already initialized.")
            return

        response.raise_for_status()
        
        data = response.json()
        print_success(f"Organization '{org}' provisioned successfully!")
        
        api_key = data.get("owner_api_key")
        if api_key:
            print_info("\nYour local API Key (store this safely):")
            console.print(f"  [bold green]{api_key}[/bold green]\n")
            console.print("Export it for future CLI usage:")
            console.print(f"  export ASILA_API_KEY={api_key}")
            
    except httpx.ConnectError:
        print_error(
            "ASILA_API_UNAVAILABLE",
            "API cannot be reached.",
            f"Failed to connect to {url}",
            "Ensure Docker is running and the API is up:\n  docker compose up -d\n  asila doctor",
            exit_code=ExitCode.DEPENDENCY_UNAVAILABLE
        )
    except httpx.HTTPStatusError as e:
        print_error(
            "ASILA_API_ERROR",
            "API returned an error.",
            f"Status code {e.response.status_code}: {e.response.text}",
            "Check API logs.",
            exit_code=ExitCode.INTERNAL_ERROR
        )
