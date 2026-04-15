"""A2A HTTP client: poll dispatches, ack, post results, heartbeat."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from computer.auth import TokenManager

log = logging.getLogger(__name__)


class A2AClient:
    """HTTP client for the A2A backend."""

    def __init__(
        self,
        base_url: str,
        operator: str,
        workspace: str,
        token_manager: TokenManager | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.operator = operator
        self.workspace = workspace
        self._token_manager = token_manager
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=10.0),
        )

    async def _auth_headers(self) -> dict[str, str]:
        """Return Authorization header if token_manager is configured and token available."""
        if self._token_manager is None:
            return {}
        token = await self._token_manager.get_token()
        if token is None:
            log.warning("TokenManager configured but returned None token — request will lack auth")
            return {}
        return {"Authorization": f"Bearer {token}"}

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()

    _POLL_TYPES = frozenset({"dispatch", "resume", "permission-response"})

    async def poll_dispatches(self) -> list[dict]:
        """GET /messages/feed with dispatch filters. Returns [] on error."""
        params = {
            "project": "computer",
            "operator": self.operator,
            "workspace": self.workspace,
            "limit": "10",
        }
        try:
            headers = await self._auth_headers()
            resp = await self._http.get(f"{self.base_url}/messages/feed", params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            messages = data.get("messages", [])
            return [m for m in messages if m.get("type") in self._POLL_TYPES]
        except (httpx.HTTPError, Exception) as exc:
            log.warning("Poll failed: %s", exc)
            return []

    async def ack_message(self, message_id: str, response: str = "dispatched") -> None:
        """POST /messages/ack to acknowledge a dispatch."""
        payload = {"message_id": message_id, "response": response}
        try:
            headers = await self._auth_headers()
            resp = await self._http.post(f"{self.base_url}/messages/ack", json=payload, headers=headers)
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
            headers = await self._auth_headers()
            resp = await self._http.post(f"{self.base_url}/messages", json=payload, headers=headers)
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
            headers = await self._auth_headers()
            resp = await self._http.post(f"{self.base_url}/messages", json=payload, headers=headers)
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
            headers = await self._auth_headers()
            resp = await self._http.post(f"{self.base_url}/messages", json=payload, headers=headers)
            resp.raise_for_status()
        except (httpx.HTTPError, Exception) as exc:
            log.warning("Post lifecycle %s failed for %s: %s", event_type, session_id, exc)

    async def post_permission_request(
        self,
        path: str,
        operation: str,
        reason: str,
        task_id: str,
    ) -> None:
        """POST /messages with type=permission-request."""
        payload = {
            "type": "permission-request",
            "from_project": "bpsai-computer",
            "to_project": "computer",
            "operator": self.operator,
            "workspace": self.workspace,
            "content": json.dumps({
                "path": path,
                "operation": operation,
                "reason": reason,
                "task_id": task_id,
            }),
        }
        try:
            headers = await self._auth_headers()
            resp = await self._http.post(f"{self.base_url}/messages", json=payload, headers=headers)
            resp.raise_for_status()
        except (httpx.HTTPError, Exception) as exc:
            log.warning("Post permission-request failed: %s", exc)

    async def post_permission_response(
        self,
        approved: bool,
        scope: str,
        ttl: int,
        request_id: str | None = None,
    ) -> None:
        """POST /messages with type=permission-response."""
        content: dict = {"approved": approved, "scope": scope, "ttl": ttl}
        if request_id is not None:
            content["request_id"] = request_id
        payload = {
            "type": "permission-response",
            "from_project": "bpsai-computer",
            "to_project": "computer",
            "operator": self.operator,
            "workspace": self.workspace,
            "content": json.dumps(content),
        }
        try:
            headers = await self._auth_headers()
            resp = await self._http.post(f"{self.base_url}/messages", json=payload, headers=headers)
            resp.raise_for_status()
        except (httpx.HTTPError, Exception) as exc:
            log.warning("Post permission-response failed: %s", exc)

    async def heartbeat(self) -> None:
        """POST heartbeat to /agents/bpsai-computer/heartbeat."""
        try:
            headers = await self._auth_headers()
            resp = await self._http.post(
                f"{self.base_url}/agents/bpsai-computer/heartbeat",
                json={"state": "running", "current_task": "Polling for dispatches", "interval_minutes": 1},
                headers=headers,
            )
            resp.raise_for_status()
        except (httpx.HTTPError, Exception) as exc:
            log.debug("Heartbeat failed: %s", exc)
