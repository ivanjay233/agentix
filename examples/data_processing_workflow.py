"""Data processing workflow example.

Demonstrates an ETL pipeline with data extraction, validation, and transformation.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agentix.core import OrchestratorEngine


async def main() -> None:
    engine = OrchestratorEngine()

    pipeline = engine.create_pipeline(
        "data-pipeline",
        stages=[
            {
                "name": "extract",
                "agent_type": "pass-through",
                "input_keys": ["source"],
                "output_keys": ["raw_data"],
                "depends_on": [],
            },
            {
                "name": "validate",
                "agent_type": "review_agent",
                "input_keys": ["raw_data"],
                "output_keys": ["validation"],
                "depends_on": ["extract"],
            },
            {
                "name": "transform",
                "agent_type": "codex",
                "input_keys": ["raw_data"],
                "output_keys": ["transformed"],
                "depends_on": ["validate"],
            },
        ],
    )

    print(f"Pipeline: {pipeline.name}")
    print(f"Stages: {len(pipeline.stages)}")
    print(f"Execution order: {pipeline.topological_sort()}")

    result = await engine.run(
        "data-pipeline",
        inputs={"source": "s3://data-bucket/events.json"},
    )

    print("\nResults:")
    for key, value in result.items():
        print(f"  {key}: {str(value)[:150]}")

    print(f"\nStages completed: {len(engine.get_board('data-pipeline').get_board_state()['done'])}")


if __name__ == "__main__":
    asyncio.run(main())
