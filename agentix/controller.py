"""Pipeline controller — manages execution lifecycle of a single pipeline."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from agentix.pipeline import Pipeline
from agentix.kanban import KanbanBoard, Task, TaskStatus
from agentix.history import ExecutionHistory

logger = logging.getLogger("agentix")


class PipelineController:
    """Controls execution of a single pipeline with lifecycle management.

    The controller owns the execution loop for one pipeline, handling
    stage-by-stage processing, pause/resume, and recording history.

    Parameters
    ----------
    pipeline : Pipeline
        The pipeline definition to control.
    board : KanbanBoard
        The board for tracking task progress.
    history : ExecutionHistory, optional
        History tracker for recording execution events.

    Examples
    --------
    >>> pipeline = Pipeline("etl")
    >>> pipeline.add_stage("extract", "reader", output_keys=["raw"])
    >>> board = KanbanBoard("etl_board")
    >>> ctrl = PipelineController(pipeline, board)
    >>> result = await ctrl.run({"source": "s3://bucket"})
    """

    def __init__(
        self,
        pipeline: Pipeline,
        board: KanbanBoard,
        history: Optional[ExecutionHistory] = None,
    ) -> None:
        self.pipeline = pipeline
        self.board = board
        self.history = history or ExecutionHistory()
        self._paused: bool = False
        self._running: bool = False

    async def run(
        self,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute the pipeline stage by stage.

        Parameters
        ----------
        inputs : dict, optional
            Initial data to seed the pipeline context.

        Returns
        -------
        dict
            Final context with outputs from every stage.
        """
        record = self.history.start(self.pipeline.name, inputs=inputs)
        self._running = True
        self._paused = False

        context: Dict[str, Any] = dict(inputs or {})
        logger.info("Starting pipeline '%s'", self.pipeline.name)

        try:
            for stage in self.pipeline.stages:
                if self._paused:
                    logger.info("Pipeline '%s' paused before stage '%s'", self.pipeline.name, stage["name"])
                    await self._wait_if_paused()

                task_id = f"{self.pipeline.name}:{stage['name']}"
                task = Task(
                    id=task_id,
                    title=stage["name"],
                    stage=stage["name"],
                    agent=stage.get("agent_type", "unknown"),
                )
                self.board.add_task(task)

                stage_input_keys = stage.get("input_keys", [])
                stage_inputs = {k: context[k] for k in stage_input_keys if k in context}

                task.update_status(TaskStatus.IN_PROGRESS)
                self.board.move_task(task_id, "in_progress")

                output = await self._process_stage(stage, stage_inputs)

                output_keys = stage.get("output_keys", [])
                if isinstance(output, dict):
                    for k in output_keys:
                        context[k] = output.get(k, None)
                elif output_keys:
                    context[output_keys[0]] = output

                task.update_status(TaskStatus.DONE)
                task.artifacts = output
                self.board.move_task(task_id, "done")

                logger.info("Stage '%s' completed", stage["name"])

        except asyncio.CancelledError:
            logger.warning("Pipeline '%s' was cancelled", self.pipeline.name)
            self.history.cancel(record)
            raise
        except Exception as exc:
            logger.error("Pipeline '%s' failed: %s", self.pipeline.name, exc)
            self.history.fail(record, str(exc))
            raise
        finally:
            self._running = False

        self.history.complete(record, outputs=context)
        return context

    def pause(self) -> None:
        """Pause execution."""
        self._paused = True
        logger.info("Pipeline '%s' paused", self.pipeline.name)

    def resume(self) -> None:
        """Resume execution."""
        self._paused = False
        logger.info("Pipeline '%s' resumed", self.pipeline.name)

    @property
    def is_running(self) -> bool:
        """Check if the pipeline is currently executing."""
        return self._running

    @property
    def is_paused(self) -> bool:
        """Check if execution is paused."""
        return self._paused

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _process_stage(self, stage: Dict[str, Any], inputs: Dict[str, Any]) -> Any:
        """Process a single stage. Override point for subclasses."""
        agent_type = stage.get("agent_type", "pass-through")
        stage_name = stage.get("name", "unnamed")
        logger.debug("Processing stage '%s' with agent '%s'", stage_name, agent_type)

        await asyncio.sleep(0.1)

        if not inputs:
            return {k: f"Generated by {agent_type}" for k in stage.get("output_keys", ["result"])}

        return inputs

    async def _wait_if_paused(self) -> None:
        """Block until unpaused, polling every second."""
        while self._paused:
            await asyncio.sleep(1)
