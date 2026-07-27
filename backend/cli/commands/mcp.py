import os
import sys
import json
import shutil
import typer
from pathlib import Path
from cli.utils.formatting import print_error, print_success, print_info, console, ExitCode

def get_mcp_config_path(client: str) -> Path | None:
    home = Path.home()
    if client == "cursor":
        return home / ".cursor" / "mcp.json"
    elif client == "claude-desktop":
        if os.name == "nt":
            return home / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
        elif sys.platform == "darwin":
            return home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        else:
            return home / ".config" / "Claude" / "claude_desktop_config.json"
    return None

def configure_mcp_command(
    client: str = typer.Option(..., "--client", help="MCP Client to configure (cursor | claude-desktop)"),
    project: str = typer.Option(None, "--project", help="Asila Project ID"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print config without writing"),
):
    """Configure an MCP client to use Asila."""
    
    if client not in ["cursor", "claude-desktop"]:
        print_error(
            "ASILA_INVALID_MCP_CLIENT",
            f"Unsupported client '{client}'.",
            "You requested auto-configuration for an unsupported client.",
            "Use one of: cursor, claude-desktop",
            exit_code=ExitCode.INVALID_ARGUMENTS
        )

    # Base SSE HTTP Server Config for Asila
    # In production/local-dev, the MCP server is hosted at /api/v1/mcp
    # Cursor/Claude requires the exact SSE URL
    asila_mcp_config = {
        "command": "uv",
        "args": [
            "run", "uvicorn", "api.main:app", "--port", "8000"
        ]
    }
    
    # We will use SSE for Claude if possible, but standard is stdio.
    # Actually, let's configure standard stdio via a direct wrapper or direct Python execution.
    asila_mcp_config = {
        "command": "python",
        "args": ["-m", "cli.main", "mcp-stdio"]
    }
    # Wait, the prompt says Asila is a FastAPI MCP server. 
    # For a dockerized setup, users usually hit the SSE endpoint or run a docker exec command.
    # Let's provide an SSE endpoint config.
    asila_sse_config = {
        "command": "curl", # Just a placeholder since Claude/Cursor might not support raw SSE without an adapter yet, 
                           # but Claude Desktop DOES support SSE via an env var or we can just use npx -y @modelcontextprotocol/inspector
    }
    
    # Best standard way for Python MCP is running the script via stdio.
    cwd = str(Path.cwd().resolve())
    api_key = os.getenv("ASILA_API_KEY", "<YOUR_API_KEY>")
    
    asila_mcp_config = {
        "command": "docker",
        "args": [
            "compose", "exec", "-e", f"ASILA_API_KEY={api_key}", "-T", "api", "python", "-m", "api.main"
        ],
        "env": {
            "ASILA_API_KEY": api_key
        }
    }

    config_path = get_mcp_config_path(client)
    
    if dry_run or not config_path:
        print_info(f"Manual JSON configuration for {client}:")
        payload = {"mcpServers": {"asila": asila_mcp_config}}
        console.print(json.dumps(payload, indent=2))
        return

    if not config_path.parent.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
    config_data = {"mcpServers": {}}
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                content = f.read().strip()
                if content:
                    config_data = json.loads(content)
        except json.JSONDecodeError:
            print_error(
                "ASILA_MCP_PARSE_ERROR",
                f"Failed to parse {config_path}",
                "The existing config file is corrupted JSON.",
                "Manually fix or delete the file.",
                exit_code=ExitCode.CONFIG_FAILURE
            )
            
    if "mcpServers" not in config_data:
        config_data["mcpServers"] = {}
        
    config_data["mcpServers"]["asila"] = asila_mcp_config
    
    # Backup
    if config_path.exists():
        backup_path = config_path.with_suffix(".json.bak")
        shutil.copy2(config_path, backup_path)
        print_info(f"Backed up existing config to {backup_path}")
        
    with open(config_path, "w") as f:
        json.dump(config_data, f, indent=2)
        
    print_success(f"Successfully injected Asila MCP configuration into {client}!")
    print_info("Restart your client to apply the changes.")
