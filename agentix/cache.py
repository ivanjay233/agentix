"""Stage-level caching to avoid re-executing completed stages."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agentix")


class StageCache:
    """Cache that stores stage outputs keyed by a hash of stage + inputs.

    Useful during development to avoid re-running expensive stages when
    upstream inputs haven't changed.

    Parameters
    ----------
    max_size : int
        Maximum number of cached entries (default: 128).
        Oldest entries are evicted when the cache is full.

    Examples
    --------
    >>> cache = StageCache()
    >>> stage = {"name": "fetch", "agent_type": "http"}
    >>> inputs = {"url": "https://example.com"}
    >>> cache.get(stage, inputs) is None
    True
    >>> cache.set(stage, inputs, {"data": "..."})
    >>> cache.get(stage, inputs)
    {'data': '...'}
    """

    def __init__(self, max_size: int = 128) -> None:
        self._max_size = max_size
        self._store: Dict[str, Any] = {}
        self._timestamps: Dict[str, datetime] = {}

    @staticmethod
    def _make_key(stage: Dict[str, Any], inputs: Dict[str, Any]) -> str:
        """Generate a deterministic cache key from stage + inputs."""
        content = json.dumps(
            {
                "name": stage.get("name"),
                "agent_type": stage.get("agent_type"),
                "inputs": {k: v for k, v in sorted(inputs.items())},
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(content.encode()).hexdigest()

    def get(self, stage: Dict[str, Any], inputs: Dict[str, Any]) -> Optional[Any]:
        """Retrieve cached output for a stage.

        Parameters
        ----------
        stage : dict
            Stage definition.
        inputs : dict
            Input data passed to the stage.

        Returns
        -------
        Any or None
            Cached output, or None if not found.
        """
        key = self._make_key(stage, inputs)
        result = self._store.get(key)
        if result is not None:
            logger.debug("Cache hit for stage '%s'", stage.get("name"))
        return result

    def set(self, stage: Dict[str, Any], inputs: Dict[str, Any], output: Any) -> None:
        """Store output in the cache, evicting old entries if needed.

        Parameters
        ----------
        stage : dict
            Stage definition.
        inputs : dict
            Input data passed to the stage.
        output : Any
            Output to cache.
        """
        key = self._make_key(stage, inputs)

        # Evict oldest if at capacity
        if len(self._store) >= self._max_size and key not in self._store:
            oldest_key = min(self._timestamps, key=lambda k: self._timestamps[k])
            del self._store[oldest_key]
            del self._timestamps[oldest_key]

        self._store[key] = output
        self._timestamps[key] = datetime.now(timezone.utc)
        logger.debug("Cached output for stage '%s'", stage.get("name"))

    def invalidate(self, stage_name: Optional[str] = None) -> int:
        """Invalidate cache entries.

        Parameters
        ----------
        stage_name : str, optional
            If provided, only invalidate entries for this stage.
            If None, clear the entire cache.

        Returns
        -------
        int
            Number of entries invalidated.
        """
        if stage_name is None:
            count = len(self._store)
            self._store.clear()
            self._timestamps.clear()
            logger.debug("Cleared entire stage cache (%d entries)", count)
            return count

        # Invalidate entries matching the stage name
        keys_to_delete: List[str] = []
        for key, entry in self._store.items():
            if isinstance(entry, dict) and entry.get("_stage_name") == stage_name:
                keys_to_delete.append(key)
            # Fallback: scan keys (less precise)
            elif stage_name in key:
                keys_to_delete.append(key)

        for key in keys_to_delete:
            del self._store[key]
            del self._timestamps[key]

        logger.debug("Invalidated %d cache entries for stage '%s'", len(keys_to_delete), stage_name)
        return len(keys_to_delete)

    def clear(self) -> None:
        """Remove all cached entries."""
        self._store.clear()
        self._timestamps.clear()

    @property
    def size(self) -> int:
        """Number of entries currently in the cache."""
        return len(self._store)
