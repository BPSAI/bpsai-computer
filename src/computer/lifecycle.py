"""Session lifecycle messages: started, complete, failed."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone

log = logging.getLogger(__name__)

_SESSION_RE = re.compile(r"^Session:\s*(.+)$")


def extract_session_id(
    stdout_lines: list[str],
    fallback_id: str | None = None,
) -> str:
    """Extract Claude Code session ID from stdout lines.

    Looks for a line matching ``Session: {id}``.  Returns the first match,
    or *fallback_id* (or a generated UUID) when no match is found.
    """
    for line in stdout_lines:
        m = _SESSION_RE.match(line.strip())
        if m:
            return m.group(1).strip()
    return fallback_id or str(uuid.uuid4())


class SessionLifecycle:
    """Posts structured lifecycle events to A2A."""

    def __init__(self, a2a: object) -> None:
        self._a2a = a2a

    async def post_started(
        self,
        session_id: str,
        operator: str,
        machine: str,
        workspace: str,
        command: str,
        resumed: bool = False,
    ) -> None:
        """Post session-started event."""
        data = {
            "operator": operator,
            "machine": machine,
            "workspace": workspace,
            "command": command,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if resumed:
            data["resumed"] = True
        await self._a2a.post_lifecycle(
            event_type="session-started",
            session_id=session_id,
            data=data,
        )

    async def post_complete(
        self,
        session_id: str,
        exit_code: int,
        duration_seconds: float,
        output_summary: str,
    ) -> None:
        """Post session-complete event. Truncates output_summary to last 10 lines."""
        lines = output_summary.strip().split("\n")
        if len(lines) > 10:
            lines = lines[-10:]
        await self._a2a.post_lifecycle(
            event_type="session-complete",
            session_id=session_id,
            data={
                "exit_code": exit_code,
                "duration_seconds": duration_seconds,
                "output_summary": "\n".join(lines),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def post_failed(
        self,
        session_id: str,
        error: str,
        exit_code: int | None,
    ) -> None:
        """Post session-failed event."""
        await self._a2a.post_lifecycle(
            event_type="session-failed",
            session_id=session_id,
            data={
                "error": error,
                "exit_code": exit_code,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
