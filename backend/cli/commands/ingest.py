import os
import json
import httpx
import typer
import mimetypes
import subprocess
from pathlib import Path
from cli.utils.formatting import print_error, print_success, print_info, console, ExitCode

def _is_within_directory(candidate: Path, directory: Path) -> bool:
    try:
        candidate.relative_to(directory)
    except ValueError:
        return False
    return True

def collect_ingest_files(path: Path) -> list[Path]:
    path = path.resolve()
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise typer.Exit(f"Path does not exist: {path}")

    git_dir = path / ".git"
    if git_dir.exists():
        result = subprocess.run(
            ["git", "-C", str(path), "ls-files", "--cached", "--others", "--exclude-standard"],
            check=True,
            capture_output=True,
            text=True,
        )
        files = []
        for relative in result.stdout.splitlines():
            candidate = path / relative
            if not candidate.is_file():
                continue
            resolved = candidate.resolve()
            if _is_within_directory(resolved, path):
                files.append(resolved)
        return sorted(files)

    ignored_directory_names = {".git", ".venv", "__pycache__", "node_modules", "dist", "build"}
    files = []
    for candidate in path.rglob("*"):
        if not candidate.is_file():
            continue
        relative_parts = candidate.relative_to(path).parts
        if any(part.startswith(".") or part in ignored_directory_names for part in relative_parts):
            continue
        resolved = candidate.resolve()
        if _is_within_directory(resolved, path):
            files.append(resolved)
    return sorted(files)

def ingest_command(
    path: Path = typer.Argument(..., help="Path to file or directory to ingest"),
    url: str = typer.Option(os.getenv("ASILA_URL", "http://localhost:8000"), "--url", help="Asila API URL"),
    api_key: str = typer.Option(os.getenv("ASILA_API_KEY"), "--api-key", help="API Key"),
    wait: bool = typer.Option(False, "--wait", help="Wait for ingestion to complete (not implemented in v1 async yet)")
):
    """Ingest a file or directory."""
    if not api_key:
        print_error(
            "ASILA_MISSING_API_KEY",
            "API key missing.",
            "You must provide an API key via ASILA_API_KEY env var or --api-key.",
            "Run 'asila init' to get an API key.",
            exit_code=ExitCode.AUTH_FAILURE
        )

    files = collect_ingest_files(path)
    if not files:
        print_info("No ingestible files found.")
        raise typer.Exit(ExitCode.INVALID_ARGUMENTS)
        
    print_info(f"Found {len(files)} files to ingest.")
    
    # We will use Rich Progress in the future, for now standard print
    root = path.resolve() if path.is_dir() else path.resolve().parent
    uploaded = []
    
    with httpx.Client(timeout=60) as client:
        for file_path in files:
            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
                
            relative_name = str(file_path.relative_to(root))
            console.print(f"Uploading {relative_name}...")
            
            try:
                response = client.post(
                    f"{url.rstrip('/')}/api/v1/knowledge/documents",
                    headers={"X-Asila-API-Key": api_key},
                    json={
                        "title": relative_name,
                        "source_uri": f"file://{file_path}",
                        "content": content,
                        "mime_type": mimetypes.guess_type(file_path.name)[0],
                        "metadata": {"path": relative_name},
                    },
                )
                response.raise_for_status()
                data = response.json()
                uploaded.append(data)
                console.print(f"[green]Queued: Job ID {data.get('embedding_job_id', 'unknown')}[/green]")
            except httpx.HTTPError as e:
                console.print(f"[red]Failed to upload {relative_name}: {e}[/red]")
                
    print_success(f"Ingestion triggered for {len(uploaded)} files.")
    
def ingest_status_command(
    job_id: str = typer.Argument(..., help="Job ID to check"),
    url: str = typer.Option(os.getenv("ASILA_URL", "http://localhost:8000"), "--url", help="Asila API URL"),
    api_key: str = typer.Option(os.getenv("ASILA_API_KEY"), "--api-key", help="API Key"),
):
    """Check ingestion status of a specific job."""
    if not api_key:
        raise typer.Exit("ASILA_API_KEY required")
        
    try:
        response = httpx.get(
            f"{url.rstrip('/')}/api/v1/knowledge/jobs/{job_id}",
            headers={"X-Asila-API-Key": api_key},
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        print_info(f"Job {job_id} Status: {data.get('status', 'unknown').upper()}")
        console.print(json.dumps(data, indent=2))
    except Exception as e:
        print_error("API_ERROR", "Failed to fetch status", str(e), "Check if backend is up.")
