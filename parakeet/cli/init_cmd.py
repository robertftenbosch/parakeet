"""Init command for Parakeet CLI."""

from pathlib import Path

import typer

from ..ui import console, print_success, print_error
from ..core.environment import (
    detect_package_manager,
    ask_install_package_manager,
    create_venv,
    get_package_manager_version,
)


def init(
    path: Path = typer.Argument(Path("."), help="Project directory to initialize"),
    venv: bool = typer.Option(False, "--venv", "-v", help="Create virtual environment"),
    python: str = typer.Option(None, "--python", "-p", help="Python version for venv (e.g., 3.11)"),
) -> None:
    """Initialize a new project with Parakeet configuration."""
    project_dir = path.resolve()
    parakeet_dir = project_dir / ".parakeet"

    if parakeet_dir.exists():
        print_error(f"Project already initialized at {project_dir}")
        raise typer.Exit(1)

    # Check for package manager if venv is requested
    if venv:
        manager = detect_package_manager()
        if manager is None:
            manager = ask_install_package_manager()
            if manager is None:
                console.print("[yellow]Continuing without virtual environment...[/]")
                venv = False

    # Create .parakeet directory
    parakeet_dir.mkdir(parents=True, exist_ok=True)

    # Create default project config
    config_file = parakeet_dir / "config.json"
    config_file.write_text('{\n  "project_name": "' + project_dir.name + '"\n}\n')

    # Create .gitignore for .parakeet
    gitignore = parakeet_dir / ".gitignore"
    gitignore.write_text("# Ignore local config\nconfig.json\n")

    # Create context file for project-specific instructions
    context_file = parakeet_dir / "context.md"
    context_file.write_text(f"""# Project Context

This file provides context to Parakeet about this project.

## Project: {project_dir.name}

## Description

Add a description of your project here.

## Tech Stack

- Add your technologies here

## Notes

Add any notes for the AI assistant here.
""")

    print_success(f"Initialized Parakeet project at {project_dir}")
    console.print(f"  [dim]Created:[/] {parakeet_dir}/")
    console.print(f"  [dim]Created:[/] {context_file}")

    # Create virtual environment if requested
    if venv:
        console.print()
        manager = detect_package_manager()
        version = get_package_manager_version(manager)
        console.print(f"[dim]Creating virtual environment with {version}...[/]")

        result = create_venv(project_dir, python_version=python)

        if "error" in result:
            print_error(result["error"])
        else:
            print_success(f"Virtual environment created at {result['path']}")
            console.print(f"  [dim]Activate with:[/] source .venv/bin/activate")

    console.print()
    console.print("[dim]Edit .parakeet/context.md to customize AI behavior for this project[/]")
