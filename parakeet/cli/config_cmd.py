"""Config command for Parakeet CLI."""

from typing import Optional

import typer

from ..core.config import load_config, save_config, CONFIG_FILE, get_ollama_config
from ..ui import console, print_success, print_error


def config(
    host: Optional[str] = typer.Option(None, "--host", help="Set Ollama server URL"),
    model: Optional[str] = typer.Option(None, "--model", help="Set model name"),
    show: bool = typer.Option(False, "--show", "-s", help="Show current configuration"),
    reset: bool = typer.Option(False, "--reset", help="Reset configuration to defaults"),
) -> None:
    """View or modify Parakeet configuration."""
    if reset:
        import os
        if CONFIG_FILE.exists():
            CONFIG_FILE.unlink()
            print_success("Configuration reset to defaults")
        else:
            console.print("[dim]No configuration file to reset[/]")
        return

    if show or (not host and not model):
        # Show current config
        current = load_config()
        console.print("\n[bold]Current Configuration:[/]")
        console.print(f"  [cyan]Config file:[/] {CONFIG_FILE}")
        console.print(f"  [cyan]Host:[/] {current.get('ollama_host', '[dim]not set[/]')}")
        console.print(f"  [cyan]Model:[/] {current.get('ollama_model', '[dim]not set[/]')}")
        console.print()
        return

    # Update config
    if host or model:
        get_ollama_config(host, model, interactive=False)
