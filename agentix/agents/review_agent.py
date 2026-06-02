"""
ReviewAgent — validates outputs and runs basic code review.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from agentix.agents.base import BaseAgent

logger = logging.getLogger("agentix")


class ReviewAgent(BaseAgent):
    """Agent that reviews outputs produced by other agents.

    Performs rudimentary checks:
      - Syntax validity (via ``compile()`` for Python).
      - Presence of common anti-patterns.
      - Length / completeness heuristics.
    """

    def __init__(self, name: str = "review_agent", config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(name=name, config=config)
        self._reviewed_count: int = 0
        self._issues_found: int = 0

    async def process(self, task: Any) -> Dict[str, Any]:
        """Review the content attached to *task*.

        Expects a dict (or object with ``.content`` / ``.artifacts``) containing
        code or text to review.

        Returns a dict with keys:
          - ``reviewed_content`` — the original content (possibly annotated)
          - ``score`` — numeric quality estimate (0–100)
          - ``issues`` — list of issue strings
          - ``passed`` — boolean
        """
        # Extract content from various input shapes
        if isinstance(task, dict):
            content = task.get("content") or task.get("artifacts", {}).get("code", "")
        else:
            content = getattr(task, "artifacts", None) or getattr(task, "content", "")
            if isinstance(content, dict):
                content = content.get("code", "")

        if not content:
            raise ValueError("ReviewAgent requires content to review.")

        logger.info("ReviewAgent reviewing content (%d chars)…", len(str(content)))

        issues: List[str] = []
        score = 100

        # --- Python syntax check ---
        if isinstance(content, str):
            try:
                compile(content, "<review>", "exec")
            except SyntaxError as exc:
                issues.append(f"Syntax error: {exc}")
                score -= 60

        # --- Anti-patterns ---
        anti_patterns = [
            ("eval(", "Use of eval() is dangerous"),
            ("exec(", "Use of exec() is dangerous"),
            ("import os", "Direct os import — consider pathlib"),
            ("pickle.load", "Unpickling untrusted data is unsafe"),
        ]
        if isinstance(content, str):
            for pattern, message in anti_patterns:
                if pattern in content:
                    issues.append(message)
                    score -= 10

        # --- Length heuristics ---
        content_str = str(content)
        if len(content_str) < 10:
            issues.append("Content is suspiciously short (< 10 chars)")
            score -= 20

        # --- Clamp score ---
        score = max(0, min(100, score))

        self._reviewed_count += 1
        self._issues_found += len(issues)

        result: Dict[str, Any] = {
            "reviewed_content": content,
            "score": score,
            "issues": issues,
            "passed": score >= 50,
        }
        logger.info("Review complete — score=%d, issues=%d", score, len(issues))
        return result

    def validate(self) -> bool:
        """ReviewAgent is always available (no external dependencies)."""
        return True

    def report(self) -> str:
        return (
            f"ReviewAgent '{self.name}' reviewed {self._reviewed_count} task(s) "
            f"and found {self._issues_found} issue(s)."
        )
