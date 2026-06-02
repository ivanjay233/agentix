"""
CodexAgent — processes coding tasks by shelling out to the codex CLI.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from typing import Any, Dict, Optional

from agentix.agents.base import BaseAgent

logger = logging.getLogger("agentix")


class CodexAgent(BaseAgent):
    """Agent that delegates code-generation tasks to the 'codex' CLI tool.

    Expects ``codex`` to be installed and available on ``PATH``.
    """

    def __init__(self, name: str = "codex_agent", config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(name=name, config=config)
        self._processed_count: int = 0

    async def process(self, task: Any) -> Dict[str, Any]:
        """Process a coding task using the codex CLI.

        Parameters
        ----------
        task : Task or dict
            Must contain at least a ``prompt`` key with the code-generation
            instruction.  Optional keys: ``language``, ``context``.

        Returns
        -------
        dict with keys ``code``, ``language``, ``raw_output``.
        """
        prompt = task.get("prompt", "") if isinstance(task, dict) else getattr(task, "prompt", "")

        if not prompt:
            raise ValueError("CodexAgent requires a 'prompt' in the task.")

        language = task.get("language", "python") if isinstance(task, dict) else getattr(task, "language", "python")

        logger.info("CodexAgent processing: language=%s, prompt=%.80s…", language, prompt)

        # Build CLI command
        cmd = ["codex", "-l", language, "-p", prompt]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
        except FileNotFoundError:
            logger.warning("'codex' CLI not found — falling back to mock output.")
            stdout = b'print("Hello from CodexAgent (mock mode)")\n'
            stderr = b""
            proc = None  # type: ignore[assignment]

        code = stdout.decode("utf-8", errors="replace").strip()
        error_output = stderr.decode("utf-8", errors="replace").strip() if stderr else ""

        self._processed_count += 1

        result: Dict[str, Any] = {
            "code": code,
            "language": language,
            "raw_output": code,
            "errors": error_output if error_output else None,
        }
        return result

    def validate(self) -> bool:
        """Check that ``codex`` is available on PATH."""
        path = shutil.which("codex")
        if path is None:
            logger.warning("Codex CLI not found on PATH — agent will use mock fallback.")
            return False
        return True

    def report(self) -> str:
        return f"CodexAgent '{self.name}' processed {self._processed_count} task(s)."
