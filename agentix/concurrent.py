"""Concurrent stage executor — runs independent stages in parallel."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Set

from agentix.pipeline import Pipeline

logger = logging.getLogger("agentix")


class ConcurrentExecutor:
    """Execute pipeline stages concurrently where dependencies permit.

    Stages that have no remaining uncompleted dependencies run in parallel.
    This is more efficient than sequential execution when the dependency
    graph contains branches.

    Parameters
    ----------
    max_concurrency : int
        Maximum number of stages to run simultaneously (default: 4).

    Examples
    --------
    >>> executor = ConcurrentExecutor(max_concurrency=2)
    >>> async def run_stage(name, inputs):
    ...     return {"result": f"{name}_done"}
    >>> results = await executor.execute(pipeline, {"start": 1}, run_stage)
    """

    def __init__(self, max_concurrency: int = 4) -> None:
        self.max_concurrency = max_concurrency

    async def execute(
        self,
        pipeline: Pipeline,
        context: Dict[str, Any],
        stage_runner,  # callable: (stage_dict, inputs) -> outputs
    ) -> Dict[str, Any]:
        """Execute pipeline stages concurrently respecting dependencies.

        Parameters
        ----------
        pipeline : Pipeline
            The pipeline to execute.
        context : dict
            Initial context (inputs).
        stage_runner : callable
            Async callable that takes (stage_dict, inputs_dict) and returns
            output dict to merge into context.

        Returns
        -------
        dict
            Final context with all stage outputs.
        """
        completed: Set[str] = set()
        pending = {s["name"] for s in pipeline.stages}
        semaphore = asyncio.Semaphore(self.max_concurrency)

        while pending:
            # Find stages whose dependencies are all satisfied
            ready = [
                s for s in pipeline.stages
                if s["name"] in pending
                and all(dep in completed for dep in s.get("depends_on", []))
            ]

            if not ready:
                raise RuntimeError(
                    f"Deadlock detected — {len(pending)} stages pending but none ready. "
                    f"Completed: {completed}"
                )

            # Run ready stages concurrently
            async def _run(stage: Dict[str, Any]) -> None:
                async with semaphore:
                    stage_inputs = {
                        k: context[k] for k in stage.get("input_keys", []) if k in context
                    }
                    logger.debug("Starting concurrent stage '%s'", stage["name"])
                    outputs = await stage_runner(stage, stage_inputs)
                    for k in stage.get("output_keys", []):
                        if isinstance(outputs, dict) and k in outputs:
                            context[k] = outputs[k]
                    completed.add(stage["name"])
                    pending.remove(stage["name"])

            await asyncio.gather(*[_run(s) for s in ready])

        return context
