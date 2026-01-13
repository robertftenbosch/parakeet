"""Chat command for Parakeet CLI."""

from typing import Optional

import typer
from ollama import Client

from ..core.config import get_ollama_config
from ..core.agent import run_agent_loop


def chat(
    host: Optional[str] = typer.Option(None, "--host", "-h", help="Ollama server URL"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model name to use"),
) -> None:
    """Start an interactive chat session with the AI agent."""
    resolved_host, resolved_model = get_ollama_config(host, model, interactive=True)
    client = Client(host=resolved_host)
    run_agent_loop(client, resolved_model)
