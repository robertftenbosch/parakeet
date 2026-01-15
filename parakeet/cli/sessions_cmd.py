"""Sessions command for managing conversation history."""

import json
from datetime import datetime
from typing import Optional

import typer
from rich.table import Table

from ..core.session import (
    list_sessions,
    delete_session,
    clear_all_sessions,
    load_session,
    get_current_session_id,
)
from ..ui.console import console

app = typer.Typer(help="Manage conversation sessions")


@app.command("list")
def list_sessions_cmd() -> None:
    """List all saved sessions."""
    sessions = list_sessions()

    if not sessions:
        console.print("[dim]No sessions found.[/]")
        return

    current_id = get_current_session_id()

    table = Table(title="Conversation Sessions", show_header=True, header_style="bold")
    table.add_column("Session ID", style="cyan")
    table.add_column("Created", style="dim")
    table.add_column("Messages", justify="right", style="yellow")
    table.add_column("Current", justify="center")

    for session in sessions:
        is_current = "✓" if session["session_id"] == current_id else ""

        # Parse and format the created_at timestamp
        try:
            created_dt = datetime.fromisoformat(session["created_at"])
            created_str = created_dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            created_str = session["created_at"]

        table.add_row(
            session["session_id"],
            created_str,
            str(session["message_count"]),
            is_current,
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(sessions)} sessions[/]")


@app.command("show")
def show_session(
    session_id: Optional[str] = typer.Argument(None, help="Session ID to show (default: current)"),
) -> None:
    """Show conversation history for a session."""
    if not session_id:
        session_id = get_current_session_id()
        if not session_id:
            console.print("[red]Error:[/] No current session found.")
            console.print("[dim]Use 'parakeet sessions list' to see available sessions.[/]")
            raise typer.Exit(1)

    conversation = load_session(session_id)

    if not conversation:
        console.print(f"[red]Error:[/] Session '{session_id}' not found.")
        raise typer.Exit(1)

    console.print(f"[bold]Session:[/] {session_id}\n")

    for msg in conversation:
        role = msg.get("role", "unknown")

        if role == "system":
            console.print("[dim]System:[/]", msg.get("content", "")[:100] + "...")
        elif role == "user":
            console.print(f"\n[bold cyan]You:[/] {msg.get('content', '')}")
        elif role == "assistant":
            content = msg.get("content", "")
            if content:
                console.print(f"[bold blue]Assistant:[/] {content}")
            if msg.get("tool_calls"):
                console.print(f"[dim]  (used {len(msg['tool_calls'])} tool(s))[/]")
        elif role == "tool":
            try:
                result = json.loads(msg.get("content", "{}"))
                # Show brief tool result
                if isinstance(result, dict) and len(result) > 0:
                    console.print(f"[dim]  Tool result: {list(result.keys())}[/]")
            except json.JSONDecodeError:
                pass

    console.print(f"\n[dim]Total messages: {len(conversation)}[/]")


@app.command("delete")
def delete_session_cmd(
    session_id: str = typer.Argument(..., help="Session ID to delete"),
) -> None:
    """Delete a specific session."""
    if delete_session(session_id):
        console.print(f"[green]✓[/] Deleted session: {session_id}")
    else:
        console.print(f"[red]Error:[/] Session '{session_id}' not found.")
        raise typer.Exit(1)


@app.command("clear")
def clear_sessions_cmd(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete all sessions."""
    if not force:
        sessions = list_sessions()
        console.print(f"[bold red]Warning:[/] This will delete {len(sessions)} session(s).")
        try:
            confirm = console.input("Are you sure? [y/N]: ").strip().lower()
            if confirm not in ("y", "yes"):
                console.print("[dim]Cancelled.[/]")
                raise typer.Exit(0)
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Cancelled.[/]")
            raise typer.Exit(0)

    count = clear_all_sessions()
    console.print(f"[green]✓[/] Deleted {count} session(s).")
