"""Workspace isolation utilities: PID files, logging, and path helpers."""

from __future__ import annotations

import logging
import os
from pathlib import Path


def _default_base_dir() -> Path:
    return Path.home() / ".bpsai-computer"


def workspace_pid_path(
    workspace: str, base_dir: Path | None = None,
) -> Path:
    """Return PID file path for a workspace: ``{base_dir}/{workspace}.pid``."""
    base = base_dir or _default_base_dir()
    return base / f"{workspace}.pid"


def write_pid_file(pid_path: Path) -> None:
    """Write the current process PID to *pid_path*."""
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(str(os.getpid()))


def remove_pid_file(pid_path: Path) -> None:
    """Remove *pid_path* if it exists (no error when missing)."""
    try:
        pid_path.unlink()
    except FileNotFoundError:
        pass


def check_existing_pid(pid_path: Path) -> int | None:
    """Return the PID stored in *pid_path* if the process is alive.

    Returns ``None`` (and deletes the stale PID file) when the process
    is no longer running.
    """
    if not pid_path.exists():
        return None
    try:
        pid = int(pid_path.read_text().strip())
    except (ValueError, OSError):
        return None

    # Check if process is still alive
    try:
        os.kill(pid, 0)
    except OSError:
        # Process is dead — clean up stale PID file
        try:
            pid_path.unlink()
        except FileNotFoundError:
            pass
        return None
    return pid


import re as _re

_SAFE_LOG_NAME_RE = _re.compile(r"[^a-zA-Z0-9_-]")


def configure_workspace_logging(workspace: str) -> None:
    """Set the root logger format to include ``[{workspace}]`` prefix."""
    safe_name = _SAFE_LOG_NAME_RE.sub("_", workspace)
    fmt = f"%(asctime)s [{safe_name}] %(levelname)s %(name)s: %(message)s"
    root = logging.getLogger()
    for handler in root.handlers:
        handler.setFormatter(logging.Formatter(fmt))
