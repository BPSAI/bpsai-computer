"""Completion detection for dispatched navigators.

Detects whether a dispatched navigator has finished work
via coordination channels or git polling.
"""

from __future__ import annotations

import subprocess
from enum import Enum
from pathlib import Path
from typing import Any


class CompletionStatus(Enum):
    IN_PROGRESS = "in_progress"
    PR_READY = "pr_ready"
    COMPLETE = "complete"
    ERROR = "error"


_COMPLETION_SIGNALS = frozenset({"sprint_complete", "sprint_done"})
_ERROR_SIGNALS = frozenset({"sprint_error", "sprint_failed"})


class CompletionDetector:
    """Detects whether a dispatched navigator has finished work."""

    def check_channel(self, channel_data: dict[str, Any]) -> CompletionStatus:
        """Check completion via channel signal data."""
        msg_type = channel_data.get("type", "")
        if msg_type in _COMPLETION_SIGNALS:
            return CompletionStatus.COMPLETE
        if msg_type in _ERROR_SIGNALS:
            return CompletionStatus.ERROR
        return CompletionStatus.IN_PROGRESS

    def check_git(self, repo_path: Path, branch: str = "") -> CompletionStatus:
        """Check completion via git polling (PR existence).

        Runs gh from within repo_path (cwd) so --repo flag is not needed.
        """
        cmd = ["gh", "pr", "list", "--head", branch, "--json", "number,state"]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True, text=True, cwd=repo_path,
            )
        except FileNotFoundError:
            return CompletionStatus.IN_PROGRESS

        if result.returncode != 0:
            return CompletionStatus.IN_PROGRESS

        stdout = result.stdout.strip()
        if not stdout or stdout == "[]":
            return CompletionStatus.IN_PROGRESS

        return CompletionStatus.PR_READY
