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
    """Return the PID stored in *pid_path*, or ``None`` if missing/invalid."""
    if not pid_path.exists():
        return None
    try:
        return int(pid_path.read_text().strip())
    except (ValueError, OSError):
        return None


def configure_workspace_logging(workspace: str) -> None:
    """Set the root logger format to include ``[{workspace}]`` prefix."""
    fmt = f"%(asctime)s [{workspace}] %(levelname)s %(name)s: %(message)s"
    root = logging.getLogger()
    for handler in root.handlers:
        handler.setFormatter(logging.Formatter(fmt))
