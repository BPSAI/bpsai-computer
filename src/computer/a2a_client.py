"""A2A HTTP client: poll dispatches, ack, post results, heartbeat."""

from __future__ import annotations

import json
import logging

import httpx

log = logging.getLogger(__name__)


class A2AClient:
    """HTTP client for the A2A backend."""

    def __init__(self, base_url: str, operator: str, workspace: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.operator = operator
        self.workspace = workspace
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=10.0),
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()

    async def poll_dispatches(self) -> list[dict]:
        """GET /messages/feed with dispatch filters. Returns [] on error."""
        params = {
            "agent": "computer",
            "operator": self.operator,
            "workspace": self.workspace,
            "limit": "10",
        }
        try:
            resp = await self._http.get(f"{self.base_url}/messages/feed", params=params)
            resp.raise_for_status()
            data = resp.json()
            messages = data.get("messages", [])
            return [m for m in messages if m.get("type") in ("dispatch", "resume")]
        except (httpx.HTTPError, Exception) as exc:
            log.warning("Poll failed: %s", exc)
            return []

    async def ack_message(self, message_id: str, response: str = "dispatched") -> None:
        """POST /messages/ack to acknowledge a dispatch."""
        payload = {"message_id": message_id, "response": response}
        try:
            resp = await self._http.post(f"{self.base_url}/messages/ack", json=payload)
            resp.raise_for_status()
        except (httpx.HTTPError, Exception) as exc:
            log.warning("Ack failed for %s: %s", message_id, exc)

    async def post_result(
        self,
        dispatch_id: str,
        content: str,
        success: bool,
    ) -> None:
        """POST /messages with type=dispatch-result."""
        payload = {
            "type": "dispatch-result",
            "from_project": "bpsai-computer",
            "to_project": "computer",
            "operator": self.operator,
            "workspace": self.workspace,
            "content": json.dumps({
                "dispatch_id": dispatch_id,
                "success": success,
                "output": content,
            }),
        }
        try:
            resp = await self._http.post(f"{self.base_url}/messages", json=payload)
            resp.raise_for_status()
        except (httpx.HTTPError, Exception) as exc:
            log.warning("Post result failed for %s: %s", dispatch_id, exc)

    async def post_session_output(
        self,
        session_id: str,
        lines: list,
    ) -> None:
        """POST /messages with type=session-output (batched streaming lines)."""
        payload = {
            "type": "session-output",
            "from_project": "bpsai-computer",
            "to_project": "computer",
            "operator": self.operator,
            "workspace": self.workspace,
            "content": json.dumps({
                "session_id": session_id,
                "lines": [
                    {
                        "line_number": line.line_number,
                        "content": line.content,
                        "stream": line.stream,
                        "timestamp": line.timestamp,
                    }
                    for line in lines
                ],
            }),
        }
        try:
            resp = await self._http.post(f"{self.base_url}/messages", json=payload)
            resp.raise_for_status()
        except (httpx.HTTPError, Exception) as exc:
            log.warning("Post session output failed for %s: %s", session_id, exc)

    async def post_lifecycle(
        self,
        event_type: str,
        session_id: str,
        data: dict,
    ) -> None:
        """POST /messages with a lifecycle event type (session-started/complete/failed)."""
        payload = {
            "type": event_type,
            "from_project": "bpsai-computer",
            "to_project": "computer",
            "operator": self.operator,
            "workspace": self.workspace,
            "content": json.dumps({"session_id": session_id, **data}),
        }
        try:
            resp = await self._http.post(f"{self.base_url}/messages", json=payload)
            resp.raise_for_status()
        except (httpx.HTTPError, Exception) as exc:
            log.warning("Post lifecycle %s failed for %s: %s", event_type, session_id, exc)

    async def heartbeat(self) -> None:
        """POST heartbeat to /agents/bpsai-computer/heartbeat."""
        try:
            resp = await self._http.post(
                f"{self.base_url}/agents/bpsai-computer/heartbeat",
                json={"state": "running", "current_task": "Polling for dispatches", "interval_minutes": 1},
            )
            resp.raise_for_status()
        except (httpx.HTTPError, Exception) as exc:
            log.debug("Heartbeat failed: %s", exc)
