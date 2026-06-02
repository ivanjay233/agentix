"""
agentix CLI — click-based command-line interface.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import click
from rich.console import Console
from rich.table import Table
from rich import box

from agentix import __version__
from agentix.core import OrchestratorEngine
from agentix.kanban import KanbanBoard

console = Console()
engine = OrchestratorEngine()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _show_board(board: KanbanBoard) -> None:
    state = board.get_board_state()
    table = Table(title=f"Kanban Board: {board.name}", box=box.ROUNDED)

    for col in board.VALID_COLUMNS:
        table.add_column(col.capitalize().replace("_", " "), style="bold")

    # Build rows — one task per row, longest column determines row count
    max_items = max(len(state[c]) for c in board.VALID_COLUMNS) if state else 0
    for i in range(max_items):
        row: list[str] = []
        for col in board.VALID_COLUMNS:
            items = state[col]
            if i < len(items):
                t = items[i]
                row.append(f"{t['id']}\n{t['title']}")
            else:
                row.append("")
        table.add_row(*row)

    console.print(table)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(__version__, prog_name="agentix")
def cli() -> None:
    """agentix — Three agents. One board. Nobody waiting on a human."""


@cli.command()
@click.argument("name", default="default", required=False)
@click.option("--stages", "-s", help="JSON string or file path listing stages")
def init(name: str, stages: Optional[str]) -> None:
    """Initialise a new pipeline and board."""
    stage_list: list[Dict[str, Any]] = []

    if stages:
        # Try as file, then as inline JSON
        if os.path.isfile(stages):
            with open(stages) as fh:
                stage_list = json.load(fh)
        else:
            stage_list = json.loads(stages)

    engine.create_pipeline(name, stages=stage_list)
    console.print(f"[green]✓[/green] Pipeline [bold]{name}[/bold] initialised with {len(stage_list)} stage(s).")


@cli.command()
@click.argument("pipeline_name", default="default", required=False)
@click.option("--inputs", "-i", help="JSON string of input variables")
def run(pipeline_name: str, inputs: Optional[str]) -> None:
    """Execute a pipeline."""
    import asyncio

    parsed_inputs: Dict[str, Any] = {}
    if inputs:
        parsed_inputs = json.loads(inputs)

    result = asyncio.run(engine.run(pipeline_name, inputs=parsed_inputs))
    console.print("[green]✓[/green] Pipeline complete.")
    for key, value in result.items():
        console.print(f"  [bold]{key}:[/bold] {str(value)[:100]}")


@cli.command()
@click.argument("pipeline_name", default="default", required=False)
def board(pipeline_name: str) -> None:
    """Display the Kanban board for a pipeline."""
    try:
        b = engine._boards[pipeline_name]
    except KeyError:
        console.print(f"[red]✗[/red] No board found for pipeline '{pipeline_name}'.")
        return
    _show_board(b)


@cli.command()
@click.argument("pipeline_name", default="default", required=False)
def status(pipeline_name: str) -> None:
    """Show pipeline execution status."""
    try:
        pipeline = engine.get_pipeline(pipeline_name)
    except KeyError:
        console.print(f"[red]✗[/red] Pipeline '{pipeline_name}' not found.")
        return

    running = "▶ Running" if engine.is_running() else "⏹ Stopped"
    paused = " ⏸ Paused" if engine.is_paused() else ""

    console.print(f"[bold]{pipeline.name}[/bold] — {running}{paused}")
    console.print(f"  Stages: {len(pipeline.stages)}")

    table = Table(box=box.SIMPLE)
    table.add_column("Stage", style="cyan")
    table.add_column("Agent", style="magenta")
    table.add_column("Depends On")

    for stage in pipeline.stages:
        deps = ", ".join(stage.get("depends_on", [])) or "—"
        table.add_row(stage["name"], stage.get("agent_type", "?"), deps)

    console.print(table)


@cli.command()
def pipelines() -> None:
    """List all registered pipelines."""
    names = engine.list_pipelines()
    if not names:
        console.print("No pipelines registered.")
        return
    console.print("[bold]Registered pipelines:[/bold]")
    for n in names:
        console.print(f"  • {n}")


if __name__ == "__main__":
    cli()
