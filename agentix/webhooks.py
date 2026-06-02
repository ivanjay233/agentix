"""Webhook notification system for pipeline events."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("agentix")


@dataclass
class WebhookConfig:
    """Configuration for a single webhook endpoint.

    Parameters
    ----------
    url : str
        Target URL to POST events to.
    headers : dict, optional
        Custom HTTP headers (e.g. Authorization).
    events : list of str, optional
        Event types to forward.  If empty, all events are forwarded.
    timeout : float
        HTTP request timeout in seconds (default: 10).
    """

    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    events: List[str] = field(default_factory=list)
    timeout: float = 10.0


class WebhookNotifier:
    """Dispatch JSON payloads to registered webhooks when pipeline events occur.

    Parameters
    ----------
    webhooks : list of WebhookConfig, optional
        Initial set of webhook endpoints.

    Examples
    --------
    >>> notifier = WebhookNotifier([
    ...     WebhookConfig(url="https://hooks.example.com/agentix", events=["stage.complete"]),
    ... ])
    >>> await notifier.notify("stage.complete", {"stage": "build", "status": "ok"})
    """

    def __init__(self, webhooks: Optional[List[WebhookConfig]] = None) -> None:
        self._webhooks: List[WebhookConfig] = webhooks or []
        self._client: Optional[httpx.AsyncClient] = None

    def add_webhook(self, config: WebhookConfig) -> None:
        """Register a new webhook endpoint.

        Parameters
        ----------
        config : WebhookConfig
            The webhook endpoint configuration.
        """
        self._webhooks.append(config)

    def remove_webhook(self, url: str) -> None:
        """Remove a webhook by URL.

        Parameters
        ----------
        url : str
            URL of the webhook to remove.
        """
        self._webhooks = [w for w in self._webhooks if w.url != url]

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy-initialized async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient()
        return self._client

    async def notify(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Dispatch an event to all matching webhooks.

        Parameters
        ----------
        event_type : str
            The type of event (e.g. "stage.complete", "pipeline.start").
        payload : dict
            JSON-serializable payload to send.
        """
        body = json.dumps({"event": event_type, "data": payload}, default=str)

        tasks = []
        for webhook in self._webhooks:
            if webhook.events and event_type not in webhook.events:
                continue
            tasks.append(self._send(webhook, body))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning("Webhook %s failed: %s", self._webhooks[i].url, result)

    async def _send(self, webhook: WebhookConfig, body: str) -> None:
        """Send a single webhook request."""
        try:
            response = await self.client.post(
                webhook.url,
                content=body,
                headers={"Content-Type": "application/json", **webhook.headers},
                timeout=webhook.timeout,
            )
            response.raise_for_status()
            logger.debug("Webhook %s responded %d", webhook.url, response.status_code)
        except httpx.HTTPError as exc:
            logger.error("Webhook %s error: %s", webhook.url, exc)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
