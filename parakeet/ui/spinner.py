"""Loading spinner for async operations."""

from contextlib import contextmanager
from rich.console import Console

console = Console()


@contextmanager
def thinking_spinner(message: str = "Thinking..."):
    """Display a spinner while processing."""
    with console.status(f"[bold blue]{message}[/]", spinner="dots"):
        yield
