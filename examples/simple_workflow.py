"""
Simple content-generation pipeline with three stages: write → review → format.

Run with:
    python examples/simple_workflow.py
"""

import asyncio
import sys
import os

# Ensure the parent package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentix.core import OrchestratorEngine
from agentix.agents.codex_agent import CodexAgent
from agentix.agents.review_agent import ReviewAgent


def build_pipeline(engine: OrchestratorEngine) -> None:
    """Register a three-stage content pipeline."""
    engine.create_pipeline(
        name="content_gen",
        stages=[
            {
                "name": "write",
                "agent_type": "codex",
                "input_keys": ["topic"],
                "output_keys": ["draft"],
                "depends_on": [],
            },
            {
                "name": "review",
                "agent_type": "review",
                "input_keys": ["draft"],
                "output_keys": ["review_report"],
                "depends_on": ["write"],
            },
            {
                "name": "format",
                "agent_type": "codex",
                "input_keys": ["draft", "review_report"],
                "output_keys": ["final"],
                "depends_on": ["review"],
            },
        ],
    )


async def main() -> None:
    engine = OrchestratorEngine()
    build_pipeline(engine)

    pipeline = engine.get_pipeline("content_gen")
    print(f"Pipeline: {pipeline.name}")
    print(f"  Stages ({len(pipeline.stages)}):")
    for s in pipeline.stages:
        deps = ", ".join(s.get("depends_on", [])) or "(none)"
        print(f"    • {s['name']}  [{s['agent_type']}]  depends_on: {deps}")

    print("\n" + "─" * 60)
    print("Running pipeline with topic='hello world'…")
    print("─" * 60)

    result = await engine.run("content_gen", inputs={"topic": "hello world"})

    print("\n" + "─" * 60)
    print("Pipeline results:")
    print("─" * 60)
    for key, value in result.items():
        val_str = str(value)[:200]
        print(f"  {key}: {val_str}")

    # Show board state
    board = engine._boards["content_gen"]
    print("\nFinal board state:")
    for col, tasks in board.get_board_state().items():
        print(f"  {col}: {len(tasks)} task(s)")
        for t in tasks:
            print(f"    [{t['id']}] {t['title']} — {t['status']}")


if __name__ == "__main__":
    asyncio.run(main())
