"""
OrchestratorEngine — manages agent lifecycle and pipeline execution.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from agentix.pipeline import Pipeline
from agentix.kanban import KanbanBoard, Task, TaskStatus

logger = logging.getLogger("agentix")


class OrchestratorEngine:
    """Central orchestrator that manages pipelines, agents, and boards."""

    def __init__(self) -> None:
        self._pipelines: Dict[str, Pipeline] = {}
        self._boards: Dict[str, KanbanBoard] = {}
        self._running: bool = False
        self._paused: bool = False
        self._tasks: List[asyncio.Task[Any]] = []

    # ------------------------------------------------------------------
    # Pipeline management
    # ------------------------------------------------------------------

    def create_pipeline(self, name: str, stages: Optional[List[Dict[str, Any]]] = None) -> Pipeline:
        """Create and register a new pipeline.

        Parameters
        ----------
        name : str
            Unique pipeline identifier.
        stages : list of dict, optional
            Each dict should contain keys: name, agent_type, input_keys, output_keys, depends_on.
        """
        if name in self._pipelines:
            raise ValueError(f"Pipeline '{name}' already exists.")

        pipeline = Pipeline(name=name, stages=stages or [])
        self._pipelines[name] = pipeline
        board = KanbanBoard(name=f"{name}_board")
        self._boards[name] = board
        logger.info("Created pipeline '%s' with %d stage(s)", name, len(pipeline.stages))
        return pipeline

    def get_pipeline(self, name: str) -> Pipeline:
        """Retrieve a registered pipeline by name."""
        if name not in self._pipelines:
            raise KeyError(f"Pipeline '{name}' not found.")
        return self._pipelines[name]

    def list_pipelines(self) -> List[str]:
        """Return names of all registered pipelines."""
        return list(self._pipelines.keys())

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def run(self, pipeline_name: str, inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a pipeline asynchronously.

        Parameters
        ----------
        pipeline_name : str
            Name of the pipeline to run.
        inputs : dict, optional
            Initial data to seed the pipeline context.

        Returns
        -------
        dict
            Final context with outputs from every stage.
        """
        if pipeline_name not in self._pipelines:
            raise KeyError(f"Pipeline '{pipeline_name}' not found.")

        pipeline = self._pipelines[pipeline_name]
        board = self._boards[pipeline_name]
        self._running = True
        self._paused = False

        context: Dict[str, Any] = dict(inputs or {})
        logger.info("Starting pipeline '%s'", pipeline_name)

        try:
            for stage in pipeline.stages:
                if self._paused:
                    logger.info("Pipeline '%s' paused before stage '%s'", pipeline_name, stage["name"])
                    await self._wait_if_paused()

                task_id = f"{pipeline_name}:{stage['name']}"
                task = Task(
                    id=task_id,
                    title=stage["name"],
                    stage=stage["name"],
                    agent=stage.get("agent_type", "unknown"),
                )
                board.add_task(task)

                # Gather inputs from context based on input_keys
                stage_input_keys = stage.get("input_keys", [])
                stage_inputs = {k: context[k] for k in stage_input_keys if k in context}

                task.update_status(TaskStatus.IN_PROGRESS)
                board.move_task(task_id, "in_progress")

                # Simulate agent processing
                output = await self._process_stage(stage, stage_inputs)

                # Store outputs in context
                output_keys = stage.get("output_keys", [])
                if isinstance(output, dict):
                    for k in output_keys:
                        context[k] = output.get(k, None)
                elif output_keys:
                    context[output_keys[0]] = output

                task.update_status(TaskStatus.DONE)
                task.artifacts = output
                board.move_task(task_id, "done")

                logger.info("Stage '%s' completed", stage["name"])

        except asyncio.CancelledError:
            logger.warning("Pipeline '%s' was cancelled", pipeline_name)
            raise
        finally:
            self._running = False

        return context

    def pause(self, pipeline_name: Optional[str] = None) -> None:
        """Pause execution of a pipeline (or all pipelines)."""
        self._paused = True
        logger.info("Pipeline execution paused")

    def resume(self, pipeline_name: Optional[str] = None) -> None:
        """Resume a paused pipeline."""
        self._paused = False
        logger.info("Pipeline execution resumed")

    def is_running(self) -> bool:
        """Check if any pipeline is currently running."""
        return self._running

    def is_paused(self) -> bool:
        """Check if pipeline execution is paused."""
        return self._paused

    def shutdown(self) -> None:
        """Cancel all pending asyncio tasks."""
        for t in self._tasks:
            t.cancel()
        self._tasks.clear()
        self._running = False
        logger.info("OrchestratorEngine shut down")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _process_stage(self, stage: Dict[str, Any], inputs: Dict[str, Any]) -> Any:
        """Process a single stage.  Override point for subclasses."""
        agent_type = stage.get("agent_type", "pass-through")
        stage_name = stage.get("name", "unnamed")
        logger.debug("Processing stage '%s' with agent '%s'", stage_name, agent_type)

        # Simulated delay so async behavior is observable
        await asyncio.sleep(0.1)

        # If inputs are empty, provide a sensible default
        if not inputs:
            return {k: f"Generated by {agent_type}" for k in stage.get("output_keys", ["result"])}

        return inputs

    async def _wait_if_paused(self) -> None:
        """Block until unpaused, polling every second."""
        while self._paused:
            await asyncio.sleep(1)
