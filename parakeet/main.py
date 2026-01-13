"""Main entry point for Parakeet CLI."""

from typing import Optional

import typer

from .cli.chat import chat
from .cli.config_cmd import config
from .cli.init_cmd import init

app = typer.Typer(
    name="parakeet",
    help="AI coding agent for biotech and robotics",
    no_args_is_help=False,
    add_completion=False,
)

app.command(name="chat")(chat)
app.command(name="config")(config)
app.command(name="init")(init)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show version"),
    host: Optional[str] = typer.Option(None, "--host", "-h", help="Ollama server URL"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model name to use"),
) -> None:
    """AI coding agent for biotech and robotics."""
    if version:
        from . import __version__
        typer.echo(f"parakeet {__version__}")
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        # Default to chat command
        chat(host=host, model=model)


if __name__ == "__main__":
    app()
