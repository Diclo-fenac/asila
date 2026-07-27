import sys
import enum
from rich.console import Console
from rich.theme import Theme
from rich.panel import Panel

# Configure a standard theme
custom_theme = Theme({
    "info": "dim cyan",
    "warning": "magenta",
    "danger": "bold red",
    "success": "bold green",
})

# Global console instance
console = Console(theme=custom_theme)
err_console = Console(theme=custom_theme, stderr=True)

class ExitCode(int, enum.Enum):
    SUCCESS = 0
    INTERNAL_ERROR = 1
    INVALID_ARGUMENTS = 2
    CONFIG_FAILURE = 3
    AUTH_FAILURE = 4
    DEPENDENCY_UNAVAILABLE = 5
    PARTIAL_SUCCESS = 6
    RATE_LIMITED = 7

def print_error(
    code: str,
    message: str,
    what_happened: str,
    how_to_fix: str,
    more_help: str | None = None,
    exit_code: ExitCode = ExitCode.INTERNAL_ERROR
) -> None:
    """
    Standardized error output for Asila CLI.
    """
    error_text = f"[danger]ERROR \\[{code}]:[/danger] {message}\n\n"
    error_text += f"[bold]What happened:[/bold]\n  {what_happened}\n\n"
    error_text += f"[bold]How to fix it:[/bold]\n{how_to_fix}\n"
    
    if more_help:
        error_text += f"\n[bold]More help:[/bold]\n  {more_help}\n"

    err_console.print(Panel(error_text, border_style="red", title="Asila Error", title_align="left"))
    sys.exit(exit_code.value)

def print_success(message: str) -> None:
    console.print(f"[success]✓[/success] {message}")

def print_warning(message: str) -> None:
    console.print(f"[warning]![/warning] {message}")

def print_info(message: str) -> None:
    console.print(f"[info]i[/info] {message}")
