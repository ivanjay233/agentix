"""
OrchestratorEngine — manages agent lifecycle and pipeline execution.

The central coordinator that registers pipelines, creates Kanban boards,
and drives stage-by-stage execution through the agent framework.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from agentix.pipeline import Pipeline
from agentix.kanban import KanbanBoard, Task, TaskStatus
from agentix.priority import Priority

logger = logging.getLogger("agentix")


class OrchestratorEngine:
    """Central orchestrator that manages pipelines, agents, and boards.

    Register pipelines via :meth:`create_pipeline`, then execute them
    asynchronously with :meth:`run`.  Use :meth:`pause` / :meth:`resume`
    to control execution flow and :meth:`shutdown` for clean teardown.

    Examples
    --------
    >>> engine = OrchestratorEngine()
    >>> engine.create_pipeline("demo", stages=[{"name": "echo", "agent_type": "pass-through"}])
    >>> import asyncio
    >>> result = asyncio.run(engine.run("demo", inputs={"msg": "hello"}))
    >>> result["msg"]
    'hello'
    """

    def __init__(self) -> None:
        """Initialise an empty orchestrator with no pipelines or boards."""
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

        Automatically creates a companion Kanban board named ``{name}_board``.

        Parameters
        ----------
        name : str
            Unique pipeline identifier.  Must not already exist.
        stages : list of dict, optional
            Each dict should contain keys:
            ``name``, ``agent_type``, ``input_keys``, ``output_keys``, ``depends_on``.

        Returns
        -------
        Pipeline
            The newly created pipeline instance.

        Raises
        ------
        ValueError
            If a pipeline with ``name`` already exists.

        Examples
        --------
        >>> engine = OrchestratorEngine()
        >>> p = engine.create_pipeline("gen", stages=[{"name": "write", "agent_type": "codex"}])
        >>> p.name
        'gen'
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
        """Retrieve a registered pipeline by name.

        Parameters
        ----------
        name : str
            Name of the pipeline to retrieve.

        Returns
        -------
        Pipeline
            The matching pipeline instance.

        Raises
        ------
        KeyError
            If no pipeline with ``name`` is registered.
        """
        if name not in self._pipelines:
            raise KeyError(f"Pipeline '{name}' not found.")
        return self._pipelines[name]

    def list_pipelines(self) -> List[str]:
        """Return names of all registered pipelines.

        Returns
        -------
        list of str
            Alphabetically sorted pipeline names.
        """
        return sorted(self._pipelines.keys())

    def get_board(self, pipeline_name: str) -> KanbanBoard:
        """Return the Kanban board associated with a pipeline.

        Parameters
        ----------
        pipeline_name : str
            Name of the pipeline whose board to retrieve.

        Returns
        -------
        KanbanBoard
            The companion board for the given pipeline.

        Raises
        ------
        KeyError
            If the pipeline has not been registered.
        """
        if pipeline_name not in self._boards:
            raise KeyError(f"No board found for pipeline '{pipeline_name}'.")
        return self._boards[pipeline_name]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def run(self, pipeline_name: str, inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a pipeline asynchronously.

        Iterates over each stage (in registration order), resolves dependencies
        from the shared context, delegates processing to the stage's agent, and
        stores outputs back into the context.

        Parameters
        ----------
        pipeline_name : str
            Name of the pipeline to run.
        inputs : dict, optional
            Initial data to seed the pipeline context (e.g. ``{"topic": "hello"}``).

        Returns
        -------
        dict
            Final context dictionary containing outputs from every stage.

        Raises
        ------
        KeyError
            If the pipeline does not exist.
        asyncio.CancelledError
            If the pipeline is cancelled during execution.

        Examples
        --------
        >>> engine = OrchestratorEngine()
        >>> engine.create_pipeline("t", stages=[{"name": "s1", "agent_type": "x", "output_keys": ["out"]}])
        >>> result = await engine.run("t", inputs={"in": 1})
        >>> "out" in result
        True
        """
        if pipeline_name not in self._pipelines:
            raise KeyError(f"Pipeline '{pipeline_name}' not found.")

        pipeline = self._pipelines[pipeline_name]
        board = self._boards[pipeline_name]
        self._running = True
        self._paused = False

        context: Dict[str, Any] = dict(inputs or {})
        logger.info("Starting pipeline '%s'", pipeline_name)

        if not pipeline.stages:
            logger.info("Pipeline '%s' has no stages — returning inputs as context", pipeline_name)
            return context

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
        """Pause execution of a pipeline (or all pipelines at once).

        Parameters
        ----------
        pipeline_name : str, optional
            Currently unused — pauses all running pipelines.
        """
        self._paused = True
        logger.info("Pipeline execution paused")

    def resume(self, pipeline_name: Optional[str] = None) -> None:
        """Resume a paused pipeline.

        Parameters
        ----------
        pipeline_name : str, optional
            Currently unused — resumes all paused pipelines.
        """
        self._paused = False
        logger.info("Pipeline execution resumed")

    def is_running(self) -> bool:
        """Check if any pipeline is currently running.

        Returns
        -------
        bool
            ``True`` if a pipeline is actively executing.
        """
        return self._running

    def is_paused(self) -> bool:
        """Check if pipeline execution is paused.

        Returns
        -------
        bool
            ``True`` if execution is paused.
        """
        return self._paused

    def shutdown(self) -> None:
        """Cancel all pending asyncio tasks and reset engine state.

        Call this during application teardown to clean up resources.
        """
        for t in self._tasks:
            t.cancel()
        self._tasks.clear()
        self._running = False
        logger.info("OrchestratorEngine shut down")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _process_stage(self, stage: Dict[str, Any], inputs: Dict[str, Any]) -> Any:
        """Process a single stage.  Override point for subclasses.

        Parameters
        ----------
        stage : dict
            Stage definition from the pipeline.
        inputs : dict
            Resolved context inputs for this stage.

        Returns
        -------
        Any
            Processing result, typically a dict or scalar.
        """
        agent_type = stage.get("agent_type", "pass-through")
        stage_name = stage.get("name", "unnamed")
        logger.debug("Processing stage '%s' with agent '%s'", stage_name, agent_type)

        # Simulated delay so async behaviour is observable
        await asyncio.sleep(0.1)

        # If inputs are empty, provide a sensible default
        if not inputs:
            return {k: f"Generated by {agent_type}" for k in stage.get("output_keys", ["result"])}

        return inputs

    async def _wait_if_paused(self) -> None:
        """Block until unpaused, polling every second."""
        while self._paused:
            await asyncio.sleep(1)
