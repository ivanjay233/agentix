"""
agentix CLI — click-based command-line interface.

Usage::

    agentix init my_pipeline
    agentix run my_pipeline --inputs '{"topic": "hello"}'
    agentix board my_pipeline
    agentix status my_pipeline
    agentix pipelines
    agentix validate my_pipeline.yaml
    agentix logs my_pipeline
    agentix template list
    agentix template show code-review --output yaml
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import click
from rich.console import Console
from rich.table import Table
from rich import box

from agentix import __version__
from agentix.core import OrchestratorEngine
from agentix.kanban import KanbanBoard
from agentix.dryrun import dry_run
from agentix.pipeline import Pipeline
from agentix.validation import validate_pipeline_config
from agentix.templates import list_presets, get_preset, get_preset_description, render_preset_yaml
from agentix.themes import get_theme, list_themes

engine = OrchestratorEngine()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _get_console(no_color: bool = False) -> Console:
    """Get a Rich Console, optionally without color."""
    return Console(no_color=no_color)


def _show_board(board: KanbanBoard, console: Console) -> None:
    """Render a Kanban board as a Rich table."""
    state = board.get_board_state()
    table = Table(title=f"Kanban Board: {board.name}", box=box.ROUNDED)

    for col in board.VALID_COLUMNS:
        table.add_column(col.capitalize().replace("_", " "), style="bold")

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


def _output_json(data: Any, console: Console) -> None:
    """Print data as JSON."""
    console.print(json.dumps(data, indent=2, default=str))


def _output_text(text: str, console: Console) -> None:
    """Print plain text."""
    console.print(text)


def _render_pipeline_table(pipeline: Pipeline, console: Console) -> None:
    """Render a pipeline's stages as a table."""
    table = Table(box=box.SIMPLE)
    table.add_column("Stage", style="cyan")
    table.add_column("Agent", style="magenta")
    table.add_column("Inputs")
    table.add_column("Outputs")
    table.add_column("Depends On")

    for stage in pipeline.stages:
        deps = ", ".join(stage.get("depends_on", [])) or "—"
        inputs = ", ".join(stage.get("input_keys", [])) or "—"
        outputs = ", ".join(stage.get("output_keys", [])) or "—"
        table.add_row(
            stage["name"],
            stage.get("agent_type", "?"),
            inputs,
            outputs,
            deps,
        )

    console.print(table)


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(__version__, prog_name="agentix")
@click.option("--no-color", is_flag=True, help="Disable colored output")
@click.option("--json-output", "json_output", is_flag=True, help="Output results as JSON")
@click.pass_context
def cli(ctx: click.Context, no_color: bool, json_output: bool) -> None:
    """agentix — Three agents. One board. Nobody waiting on a human."""
    ctx.ensure_object(dict)
    ctx.obj["no_color"] = no_color
    ctx.obj["json_output"] = json_output


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("name", default="default", required=False)
@click.option("--stages", "-s", help="JSON string or file path listing stages")
@click.pass_context
def init(ctx: click.Context, name: str, stages: Optional[str]) -> None:
    """Initialise a new pipeline and board."""
    console = _get_console(ctx.obj["no_color"])
    json_output = ctx.obj["json_output"]

    stage_list: list[Dict[str, Any]] = []

    if stages:
        if os.path.isfile(stages):
            with open(stages) as fh:
                stage_list = json.load(fh)
        else:
            stage_list = json.loads(stages)

    engine.create_pipeline(name, stages=stage_list)

    if json_output:
        _output_json({"pipeline": name, "stages": len(stage_list)}, console)
    else:
        console.print(f"[green]✓[/green] Pipeline [bold]{name}[/bold] initialised with {len(stage_list)} stage(s).")


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("pipeline_name", default="default", required=False)
@click.option("--inputs", "-i", help="JSON string of input variables")
@click.pass_context
def run(ctx: click.Context, pipeline_name: str, inputs: Optional[str]) -> None:
    """Execute a pipeline."""
    import asyncio

    console = _get_console(ctx.obj["no_color"])
    json_output = ctx.obj["json_output"]

    parsed_inputs: Dict[str, Any] = {}
    if inputs:
        parsed_inputs = json.loads(inputs)

    result = asyncio.run(engine.run(pipeline_name, inputs=parsed_inputs))

    if json_output:
        _output_json(result, console)
    else:
        console.print("[green]✓[/green] Pipeline complete.")
        for key, value in result.items():
            console.print(f"  [bold]{key}:[/bold] {str(value)[:100]}")


# ---------------------------------------------------------------------------
# board
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("pipeline_name", default="default", required=False)
@click.pass_context
def board(ctx: click.Context, pipeline_name: str) -> None:
    """Display the Kanban board for a pipeline."""
    console = _get_console(ctx.obj["no_color"])
    json_output = ctx.obj["json_output"]

    try:
        b = engine._boards[pipeline_name]
    except KeyError:
        console.print(f"[red]✗[/red] No board found for pipeline '{pipeline_name}'.")
        return

    if json_output:
        _output_json(b.get_board_state(), console)
    else:
        _show_board(b, console)


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("pipeline_name", default="default", required=False)
@click.pass_context
def status(ctx: click.Context, pipeline_name: str) -> None:
    """Show pipeline execution status."""
    console = _get_console(ctx.obj["no_color"])
    json_output = ctx.obj["json_output"]

    try:
        pipeline = engine.get_pipeline(pipeline_name)
    except KeyError:
        console.print(f"[red]✗[/red] Pipeline '{pipeline_name}' not found.")
        return

    if json_output:
        _output_json(
            {
                "name": pipeline.name,
                "stages": len(pipeline.stages),
                "running": engine.is_running(),
                "paused": engine.is_paused(),
            },
            console,
        )
        return

    running = "▶ Running" if engine.is_running() else "⏹ Stopped"
    paused = " ⏸ Paused" if engine.is_paused() else ""

    console.print(f"[bold]{pipeline.name}[/bold] — {running}{paused}")
    console.print(f"  Stages: {len(pipeline.stages)}")
    _render_pipeline_table(pipeline, console)


# ---------------------------------------------------------------------------
# pipelines
# ---------------------------------------------------------------------------


@cli.command()
@click.pass_context
def pipelines(ctx: click.Context) -> None:
    """List all registered pipelines."""
    console = _get_console(ctx.obj["no_color"])
    json_output = ctx.obj["json_output"]

    names = engine.list_pipelines()
    if json_output:
        _output_json({"pipelines": names}, console)
        return

    if not names:
        console.print("No pipelines registered.")
        return
    console.print("[bold]Registered pipelines:[/bold]")
    for n in names:
        console.print(f"  • {n}")


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("pipeline_name", default="default", required=False)
@click.option("--output", "-o", type=click.Choice(["yaml", "json"]), default="yaml", help="Output format")
@click.pass_context
def export(ctx: click.Context, pipeline_name: str, output: str) -> None:
    """Export a pipeline definition."""
    console = _get_console(ctx.obj["no_color"])

    try:
        p = engine.get_pipeline(pipeline_name)
    except KeyError:
        console.print(f"[red]✗[/red] Pipeline '{pipeline_name}' not found.")
        return

    if output == "yaml":
        console.print(p.to_yaml())
    else:
        data = {"name": p.name, "stages": p.stages}
        console.print(json.dumps(data, indent=2))


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("file", type=click.Path(exists=True))
@click.pass_context
def validate(ctx: click.Context, file: str) -> None:
    """Validate a pipeline YAML/JSON configuration file."""
    import yaml

    console = _get_console(ctx.obj["no_color"])
    json_output = ctx.obj["json_output"]

    try:
        with open(file) as fh:
            if file.endswith((".yaml", ".yml")):
                data = yaml.safe_load(fh)
            else:
                data = json.load(fh)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to parse '{file}': {e}")
        return

    if not isinstance(data, dict):
        console.print("[red]✗[/red] Config must be a dictionary/mapping.")
        return

    # Validate using dry-run logic
    pipeline = Pipeline(name=data.get("name", "unnamed"), stages=data.get("stages", []))
    result = dry_run(pipeline)

    if json_output:
        _output_json(result.to_dict(), console)
        return

    if result.valid:
        console.print("[green]✓[/green] Pipeline configuration is valid.")
        if result.stage_order:
            console.print(f"  Execution order: {' -> '.join(result.stage_order)}")
    else:
        console.print(f"[red]✗[/red] Pipeline configuration has {len(result.errors)} error(s):")
        for err in result.errors:
            console.print(f"  • [red]{err}[/red]")

    if result.warnings:
        console.print(f"\n[yellow]⚠[/yellow] Warnings ({len(result.warnings)}):")
        for w in result.warnings:
            console.print(f"  • [yellow]{w}[/yellow]")


# ---------------------------------------------------------------------------
# logs
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("pipeline_name", default="default", required=False)
@click.option("--limit", "-n", default=10, help="Number of recent executions to show")
@click.pass_context
def logs(ctx: click.Context, pipeline_name: str, limit: int) -> None:
    """Show execution history for a pipeline."""
    console = _get_console(ctx.obj["no_color"])
    json_output = ctx.obj["json_output"]

    try:
        p = engine.get_pipeline(pipeline_name)
    except KeyError:
        console.print(f"[red]✗[/red] Pipeline '{pipeline_name}' not found.")
        return

    history = p._history if hasattr(p, "_history") else []

    if json_output:
        _output_json(
            {"pipeline": pipeline_name, "executions": [r.to_dict() for r in history[:limit]]},
            console,
        )
        return

    if not history:
        console.print(f"No execution history for pipeline '{pipeline_name}'.")
        return

    console.print(f"[bold]Execution history for '{pipeline_name}':[/bold]")
    for record in history[:limit]:
        status_style = {
            "completed": "green",
            "failed": "red",
            "cancelled": "yellow",
            "running": "cyan",
        }.get(record.status, "white")
        console.print(
            f"  • [{status_style}]{record.status}[/{status_style}] "
            f"(started: {record.started_at.isoformat()})"
        )


# ---------------------------------------------------------------------------
# template
# ---------------------------------------------------------------------------


@cli.group()
def template() -> None:
    """Manage pipeline templates/presets."""


@template.command("list")
@click.pass_context
def template_list(ctx: click.Context) -> None:
    """List available pipeline templates."""
    console = _get_console(ctx.obj["no_color"])
    json_output = ctx.obj["json_output"]

    presets = list_presets()

    if json_output:
        data = {}
        for name in presets:
            desc = get_preset_description(name)
            data[name] = desc or ""
        _output_json({"templates": data}, console)
        return

    if not presets:
        console.print("No templates available.")
        return

    console.print("[bold]Available pipeline templates:[/bold]")
    for name in presets:
        desc = get_preset_description(name)
        console.print(f"  • [cyan]{name}[/cyan] — {desc}")


@template.command("show")
@click.argument("name")
@click.option("--output", "-o", type=click.Choice(["yaml", "json"]), default="yaml", help="Output format")
@click.pass_context
def template_show(ctx: click.Context, name: str, output: str) -> None:
    """Show a specific pipeline template."""
    console = _get_console(ctx.obj["no_color"])

    preset = get_preset(name)
    if preset is None:
        console.print(f"[red]✗[/red] Template '{name}' not found.")
        console.print(f"Available: {', '.join(list_presets())}")
        return

    if output == "yaml":
        yaml_str = render_preset_yaml(name)
        console.print(yaml_str)
    else:
        data = {"name": preset["name"], "stages": preset["stages"]}
        console.print(json.dumps(data, indent=2))


@template.command("init")
@click.argument("template_name")
@click.argument("pipeline_name", default=None, required=False)
@click.pass_context
def template_init(ctx: click.Context, template_name: str, pipeline_name: Optional[str]) -> None:
    """Initialise a pipeline from a template."""
    console = _get_console(ctx.obj["no_color"])

    preset = get_preset(template_name)
    if preset is None:
        console.print(f"[red]✗[/red] Template '{template_name}' not found.")
        console.print(f"Available: {', '.join(list_presets())}")
        return

    name = pipeline_name or preset["name"]
    engine.create_pipeline(name, stages=preset["stages"])
    console.print(
        f"[green]✓[/green] Pipeline [bold]{name}[/bold] initialised "
        f"from template [cyan]{template_name}[/cyan] "
        f"with {len(preset['stages'])} stage(s)."
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
