"""Interactive plan selection UI."""

from typing import Optional
from rich.table import Table
from rich.panel import Panel
from .console import console


def select_plan_steps(plan_title: str, steps: list[dict[str, str]]) -> list[int]:
    """Present a plan and let user select which steps to execute.

    Args:
        plan_title: Title of the plan
        steps: List of step dicts with 'description' and optionally 'agent'

    Returns:
        List of step indices (0-based) that user selected
    """
    if not steps:
        return []

    # Display plan
    console.print()
    console.print(Panel(
        f"[bold cyan]{plan_title}[/]",
        title="📋 Plan Proposal",
        border_style="cyan"
    ))
    console.print()

    # Create table with steps
    table = Table(show_header=True, header_style="bold", border_style="dim")
    table.add_column("#", justify="right", style="cyan", width=4)
    table.add_column("Step", style="white")
    table.add_column("Agent", style="magenta", width=15)
    table.add_column("Selected", justify="center", width=10)

    for i, step in enumerate(steps, 1):
        description = step.get("description", "")
        agent = step.get("agent", "default")
        table.add_row(str(i), description, agent, "☐")

    console.print(table)
    console.print()

    # Selection instructions
    console.print("[dim]Select steps to execute:[/]")
    console.print("  • Enter step numbers separated by spaces (e.g., '1 2 4')")
    console.print("  • Enter 'all' to select all steps")
    console.print("  • Enter 'none' or leave empty to cancel")
    console.print()

    # Get user selection
    while True:
        try:
            selection = console.input("[bold green]Select steps:[/] ").strip().lower()

            if not selection or selection == "none":
                console.print("[yellow]No steps selected. Plan cancelled.[/]")
                return []

            if selection == "all":
                selected_indices = list(range(len(steps)))
                break

            # Parse numbers
            try:
                numbers = [int(n.strip()) for n in selection.split()]
                # Validate numbers
                invalid = [n for n in numbers if n < 1 or n > len(steps)]
                if invalid:
                    console.print(f"[red]Invalid step numbers: {invalid}[/]")
                    console.print(f"[dim]Please enter numbers between 1 and {len(steps)}[/]")
                    continue

                # Convert to 0-based indices and remove duplicates
                selected_indices = sorted(list(set(n - 1 for n in numbers)))
                break

            except ValueError:
                console.print("[red]Invalid input. Please enter numbers, 'all', or 'none'.[/]")
                continue

        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Plan cancelled.[/]")
            return []

    # Show selected steps
    console.print()
    console.print("[bold green]Selected steps:[/]")
    for idx in selected_indices:
        step = steps[idx]
        agent = step.get("agent", "default")
        console.print(f"  ✓ [cyan]{idx + 1}.[/] {step['description']} [dim]({agent})[/]")

    console.print()

    # Confirm
    try:
        confirm = console.input("[bold]Execute these steps? [Y/n]:[/] ").strip().lower()
        if confirm in ('', 'y', 'yes', 'ja'):
            return selected_indices
        else:
            console.print("[yellow]Plan cancelled.[/]")
            return []
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Plan cancelled.[/]")
        return []


def display_plan_summary(plan_title: str, steps: list[dict[str, str]], selected_indices: list[int]) -> None:
    """Display a summary of the plan with selected steps highlighted.

    Args:
        plan_title: Title of the plan
        steps: All plan steps
        selected_indices: Indices of selected steps
    """
    console.print()
    console.print(Panel(
        f"[bold green]Executing Plan: {plan_title}[/]",
        border_style="green"
    ))

    for i, step in enumerate(steps):
        if i in selected_indices:
            console.print(f"  [green]✓[/] [bold]{step['description']}[/] [dim]({step.get('agent', 'default')})[/]")
        else:
            console.print(f"  [dim]○ {step['description']} (skipped)[/]")

    console.print()
