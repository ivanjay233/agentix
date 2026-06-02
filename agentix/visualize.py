"""Dependency graph visualization for pipelines."""

from __future__ import annotations

from typing import Any, Dict, List

from agentix.pipeline import Pipeline


def dependency_graph_mermaid(pipeline: Pipeline) -> str:
    """Generate a Mermaid flowchart from a pipeline's dependency graph.

    Parameters
    ----------
    pipeline : Pipeline
        The pipeline to visualize.

    Returns
    -------
    str
        Mermaid markup string suitable for embedding in Markdown or
        rendering with the Mermaid CLI/libraries.

    Examples
    --------
    >>> from agentix.pipeline import Pipeline
    >>> p = Pipeline("test")
    >>> p.add_stage("a", "agent", output_keys=["x"])
    >>> p.add_stage("b", "agent", input_keys=["x"], depends_on=["a"])
    >>> print(dependency_graph_mermaid(p))
    flowchart LR
        a["a<br/><small>agent</small>"] --> b["b<br/><small>agent</small>"]
    """
    lines: List[str] = ["flowchart LR"]

    for stage in pipeline.stages:
        name = stage["name"]
        agent = stage.get("agent_type", "?")
        node_id = name.replace(" ", "_").replace("-", "_")
        lines.append(f'    {node_id}["{name}<br/><small>{agent}</small>"]')

    for stage in pipeline.stages:
        name = stage["name"]
        node_id = name.replace(" ", "_").replace("-", "_")
        for dep in stage.get("depends_on", []):
            dep_id = dep.replace(" ", "_").replace("-", "_")
            lines.append(f"    {dep_id} --> {node_id}")

    return "\n".join(lines)


def dependency_graph_dot(pipeline: Pipeline) -> str:
    """Generate a Graphviz DOT string from a pipeline's dependency graph.

    Parameters
    ----------
    pipeline : Pipeline
        The pipeline to visualize.

    Returns
    -------
    str
        DOT format string for use with Graphviz tools (dot, neato, etc.).
    """
    lines: List[str] = [
        "digraph Pipeline {",
        '    rankdir=LR;',
        '    node [shape=box, style=rounded];',
    ]

    for stage in pipeline.stages:
        name = stage["name"]
        agent = stage.get("agent_type", "?")
        node_id = name.replace(" ", "_").replace("-", "_")
        lines.append(f'    {node_id} [label="{name}\\n({agent})"];')

    for stage in pipeline.stages:
        name = stage["name"]
        node_id = name.replace(" ", "_").replace("-", "_")
        for dep in stage.get("depends_on", []):
            dep_id = dep.replace(" ", "_").replace("-", "_")
            lines.append(f"    {dep_id} -> {node_id};")

    lines.append("}")
    return "\n".join(lines)
