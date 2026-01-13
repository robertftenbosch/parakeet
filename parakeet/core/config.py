"""Configuration management for Parakeet."""

import json
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from ollama import Client

load_dotenv()

CONFIG_DIR = Path.home() / ".parakeet"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict[str, str]:
    """Load config from ~/.parakeet/config.json or return empty dict."""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_config(config: dict[str, str]) -> None:
    """Save config to ~/.parakeet/config.json."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")


def list_available_models(client: Client) -> list[str]:
    """Get list of available models from Ollama."""
    try:
        response = client.list()
        return [model['name'] for model in response.get('models', [])]
    except Exception:
        return []


def get_ollama_config(
    host: Optional[str] = None,
    model: Optional[str] = None,
    interactive: bool = True
) -> tuple[str, str]:
    """
    Determine Ollama host and model based on priority:
    1. Function arguments
    2. Config file
    3. Environment variables
    4. Interactive prompt (if enabled)
    """
    from ..ui import console, print_success

    config = load_config()

    # Determine host
    resolved_host = (
        host or
        config.get("ollama_host") or
        os.environ.get("OLLAMA_HOST") or
        "http://localhost:11434"
    )

    # Create client to check connection / list models
    client = Client(host=resolved_host)

    # Determine model
    resolved_model = model or config.get("ollama_model") or os.environ.get("OLLAMA_MODEL")

    if not resolved_model and interactive:
        console.print(f"[dim]Connected to Ollama at:[/] {resolved_host}")
        resolved_model = select_model_interactive(client)

    if not resolved_model:
        resolved_model = "llama3.2"  # fallback default

    # Save to config if changed
    if resolved_host != config.get("ollama_host") or resolved_model != config.get("ollama_model"):
        config["ollama_host"] = resolved_host
        config["ollama_model"] = resolved_model
        save_config(config)
        print_success(f"Configuration saved to {CONFIG_FILE}")

    return resolved_host, resolved_model


def select_model_interactive(client: Client) -> Optional[str]:
    """Show available models and let user select one."""
    from ..ui import console, print_error

    models = list_available_models(client)
    if not models:
        print_error("No models found. Please pull a model first: ollama pull <model>")
        return None

    console.print("\n[bold]Available models:[/]")
    for i, model in enumerate(models, 1):
        console.print(f"  [cyan]{i}.[/] {model}")

    while True:
        try:
            choice = console.input("\n[bold]Select model number:[/] ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(models):
                return models[idx]
            console.print(f"[red]Please enter a number between 1 and {len(models)}[/]")
        except ValueError:
            console.print("[red]Please enter a valid number[/]")
        except (KeyboardInterrupt, EOFError):
            return None
