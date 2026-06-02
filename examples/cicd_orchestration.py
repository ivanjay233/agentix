"""CI/CD orchestration example.

Demonstrates a build -> test -> deploy pipeline.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agentix.core import OrchestratorEngine
from agentix.dryrun import dry_run


async def main() -> None:
    engine = OrchestratorEngine()

    pipeline = engine.create_pipeline(
        "ci-cd",
        stages=[
            {
                "name": "build",
                "agent_type": "codex",
                "input_keys": ["source"],
                "output_keys": ["build_artifact"],
                "depends_on": [],
            },
            {
                "name": "test",
                "agent_type": "review_agent",
                "input_keys": ["build_artifact"],
                "output_keys": ["test_results"],
                "depends_on": ["build"],
            },
            {
                "name": "package",
                "agent_type": "pass-through",
                "input_keys": ["build_artifact"],
                "output_keys": ["package"],
                "depends_on": ["test"],
            },
            {
                "name": "deploy",
                "agent_type": "pass-through",
                "input_keys": ["package"],
                "output_keys": ["deployment"],
                "depends_on": ["package"],
            },
        ],
    )

    print(f"Pipeline: {pipeline.name}")
    print(f"Stages: {len(pipeline.stages)}")

    # Dry-run first
    dry_result = dry_run(pipeline)
    print(f"\nDry-run: {'✓ Valid' if dry_result.valid else '✗ Invalid'}")
    print(f"Execution order: {dry_result.stage_order}")

    # Execute
    result = await engine.run(
        "ci-cd",
        inputs={"source": "https://github.com/user/repo.git"},
    )

    print("\nResults:")
    for key, value in result.items():
        print(f"  {key}: {str(value)[:150]}")

    # Show board state
    board = engine.get_board("ci-cd")
    state = board.get_board_state()
    print(f"\nBoard: {board.name}")
    for col, tasks in state.items():
        print(f"  {col}: {len(tasks)} task(s)")


if __name__ == "__main__":
    asyncio.run(main())
