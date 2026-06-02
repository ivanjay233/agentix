"""Code review pipeline example.

Demonstrates a multi-stage pipeline for automated code review.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agentix.core import OrchestratorEngine


async def main() -> None:
    engine = OrchestratorEngine()

    pipeline = engine.create_pipeline(
        "code-review",
        stages=[
            {
                "name": "lint",
                "agent_type": "review_agent",
                "input_keys": ["source_code"],
                "output_keys": ["lint_results"],
                "depends_on": [],
            },
            {
                "name": "analyze",
                "agent_type": "review_agent",
                "input_keys": ["source_code"],
                "output_keys": ["analysis"],
                "depends_on": [],
            },
            {
                "name": "report",
                "agent_type": "codex",
                "input_keys": ["lint_results", "analysis"],
                "output_keys": ["final_report"],
                "depends_on": ["lint", "analyze"],
            },
        ],
    )

    print(f"Pipeline: {pipeline.name}")
    print(f"Stages: {len(pipeline.stages)}")

    result = await engine.run(
        "code-review",
        inputs={
            "source_code": """
def add(a, b):
    return a + b

eval("print('bad')")
""",
        },
    )

    print("\nResults:")
    for key, value in result.items():
        print(f"  {key}: {str(value)[:200]}")

    board = engine.get_board("code-review")
    print(f"\nBoard state: {board.get_board_state()['done']} task(s) completed")


if __name__ == "__main__":
    asyncio.run(main())
