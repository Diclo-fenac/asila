import os
import typer
from typing import Optional
from typing_extensions import Annotated
from rich.console import Console

# We will import commands as we build them.
# For now, we set up the structure.
from cli.utils.formatting import print_error, ExitCode
from cli.commands.init import init_command
from cli.commands.doctor import doctor_command
from cli.commands.mcp import configure_mcp_command
from cli.commands.ingest import ingest_command, ingest_status_command
from cli.commands.search import search_command
from cli.commands.org import create_org_command
from cli.commands.key import create_key_command, list_keys_command, revoke_key_command, rotate_key_command
from cli.commands.documents import list_docs_command, delete_doc_command
from cli.commands.jobs import get_job_command
from cli.commands.audit import list_audit_command, verify_audit_command

app = typer.Typer(
    name="asila",
    help="Asila knowledge platform CLI",
    no_args_is_help=True,
    add_completion=False,
)

# Placeholder for sub-apps
sources_app = typer.Typer(name="sources", help="Manage data sources", no_args_is_help=True)
mcp_app = typer.Typer(name="mcp", help="Configure MCP clients", no_args_is_help=True)
config_app = typer.Typer(name="config", help="Manage CLI configuration", no_args_is_help=True)
org_app = typer.Typer(name="org", help="Manage organizations", no_args_is_help=True)
key_app = typer.Typer(name="key", help="Manage API keys", no_args_is_help=True)
docs_app = typer.Typer(name="documents", help="Manage knowledge documents", no_args_is_help=True)
jobs_app = typer.Typer(name="jobs", help="Inspect ingestion jobs", no_args_is_help=True)
audit_app = typer.Typer(name="audit", help="Verify and inspect security audit logs", no_args_is_help=True)

app.add_typer(sources_app)
app.add_typer(config_app)
app.add_typer(org_app)
app.add_typer(key_app)
app.add_typer(docs_app)
app.add_typer(jobs_app)
app.add_typer(audit_app)

mcp_app.command("configure")(configure_mcp_command)
app.add_typer(mcp_app)

org_app.command("create")(create_org_command)

key_app.command("create")(create_key_command)
key_app.command("list")(list_keys_command)
key_app.command("revoke")(revoke_key_command)
key_app.command("rotate")(rotate_key_command)

docs_app.command("list")(list_docs_command)
docs_app.command("delete")(delete_doc_command)

jobs_app.command("get")(get_job_command)

audit_app.command("list")(list_audit_command)
audit_app.command("verify")(verify_audit_command)

app.command("init")(init_command)
app.command("doctor")(doctor_command)
app.command("status")(doctor_command)
app.command("ingest")(ingest_command)
app.command("ingest-status")(ingest_status_command)
app.command("search")(search_command)

@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
):
    """
    Asila knowledge platform CLI.
    """
    # Store global state if needed
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["json"] = json_output


@app.command()
def version():
    """Show the CLI version."""
    # Would typically pull from importlib.metadata or __version__
    typer.echo("asila CLI version 0.1.0")

if __name__ == "__main__":
    app()
