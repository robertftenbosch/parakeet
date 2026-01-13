"""Rich console setup and output utilities."""

import re
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()


def print_code(code: str, language: str = "python") -> None:
    """Print code with syntax highlighting."""
    syntax = Syntax(code, language, theme="monokai", line_numbers=True)
    console.print(syntax)


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[bold red]Error:[/] {message}")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[bold green]✓[/] {message}")


def print_tool(tool_name: str, args: dict) -> None:
    """Print a tool invocation."""
    console.print(f"[bold yellow]Tool:[/] {tool_name}({args})")


def print_assistant(content: str) -> None:
    """Print assistant response with markdown rendering."""
    # Check if content contains code blocks
    if "```" in content:
        # Render as markdown to get syntax highlighting
        md = Markdown(content)
        console.print(md)
    else:
        console.print(f"[bold blue]Assistant:[/] {content}")


def extract_code_blocks(text: str) -> list[tuple[str, str]]:
    """Extract code blocks from markdown text.

    Returns list of (language, code) tuples.
    """
    pattern = r"```(\w*)\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    return [(lang or "text", code.strip()) for lang, code in matches]
