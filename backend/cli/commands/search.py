import os
import json
import httpx
import typer
from cli.utils.formatting import print_error, print_success, print_info, print_warning, console, ExitCode

def search_command(
    query: str = typer.Argument(..., help="Search query"),
    url: str = typer.Option(os.getenv("ASILA_URL", "http://localhost:8000"), "--url", help="Asila API URL"),
    api_key: str = typer.Option(os.getenv("ASILA_API_KEY"), "--api-key", help="API Key"),
    limit: int = typer.Option(10, "--limit", help="Number of results"),
    mode: str = typer.Option("hybrid", "--mode", help="Search mode (keyword | hybrid | semantic)"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON")
):
    """Search indexed knowledge."""
    if not api_key:
        print_error(
            "ASILA_MISSING_API_KEY",
            "API key missing.",
            "You must provide an API key via ASILA_API_KEY env var or --api-key.",
            "Run 'asila init' to get an API key.",
            exit_code=ExitCode.AUTH_FAILURE
        )

    try:
        response = httpx.get(
            f"{url.rstrip('/')}/api/v1/knowledge/retrieval/search",
            headers={"X-Asila-API-Key": api_key},
            params={"query": query, "limit": limit, "mode": mode},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        
        if json_output:
            console.print(json.dumps(data, indent=2))
            return
            
        results = data.get("results", [])
        if not results:
            print_warning("No results found. Try broadening your query or switching mode.")
            return
            
        print_info(f"Found {len(results)} results (mode: {mode}):\n")
        
        for idx, res in enumerate(results, 1):
            title = res.get("title", "Unknown")
            source = res.get("source_uri", "Unknown")
            score = res.get("score", 0.0)
            content = res.get("content", "").strip()
            # truncate content for display
            if len(content) > 300:
                content = content[:300] + "..."
                
            console.print(f"[bold cyan]{idx}. {title}[/bold cyan] (Score: {score:.3f})")
            console.print(f"[dim]{source}[/dim]")
            console.print(f"{content}\n")
            
    except httpx.HTTPError as e:
        print_error("API_ERROR", "Search failed.", str(e), "Check if backend is up.", exit_code=ExitCode.INTERNAL_ERROR)
