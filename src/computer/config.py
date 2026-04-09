"""Daemon configuration: dataclass + YAML loader with CLI overrides."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field, fields
from pathlib import Path

import yaml

_WORKSPACE_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def validate_workspace_name(name: str) -> None:
    """Raise ValueError if *name* is not a safe workspace identifier."""
    if not name or not _WORKSPACE_NAME_RE.match(name):
        raise ValueError(
            f"Invalid workspace name {name!r}. "
            "Must match ^[a-zA-Z0-9_-]+$ (no paths or special chars)."
        )


def _default_workspace_root() -> str:
    return os.environ.get(
        "BPSAI_WORKSPACE_ROOT",
        str(Path.home() / "workspace"),
    )


@dataclass
class DaemonConfig:
    """Configuration for the dispatch daemon."""

    operator: str
    workspace: str
    workspace_root: str = field(default_factory=_default_workspace_root)
    a2a_url: str = "https://a2a.paircoder.ai"
    paircoder_api_url: str = "https://api.paircoder.ai"
    license_id: str | None = None
    poll_interval: int = 5
    process_timeout: int = 1800
    stream_batch_interval: float = 2.0
    stream_buffer_limit: int = 1000

    def __post_init__(self):
        self.poll_interval = int(self.poll_interval)
        self.process_timeout = int(self.process_timeout)
        self.stream_batch_interval = float(self.stream_batch_interval)
        self.stream_buffer_limit = int(self.stream_buffer_limit)


def _default_config_dir() -> Path:
    return Path.home() / ".bpsai-computer"


def _resolve_config_path(
    config_dir: Path,
    workspace: str | None,
) -> Path | None:
    """Resolve config file path based on workspace name.

    When workspace provided: try {workspace}.yaml first, then config.yaml.
    When no workspace: try config.yaml only.
    Returns None if no config file found.
    """
    if workspace:
        ws_path = config_dir / f"{workspace}.yaml"
        if ws_path.exists():
            return ws_path
    default_path = config_dir / "config.yaml"
    if default_path.exists():
        return default_path
    return None


def load_config(
    config_path: Path | None = None,
    overrides: dict | None = None,
    workspace: str | None = None,
) -> DaemonConfig:
    """Load config from YAML file, then apply CLI overrides.

    When *workspace* is given and *config_path* is not, resolves the config
    file as ``~/.bpsai-computer/{workspace}.yaml`` first, falling back to
    ``~/.bpsai-computer/config.yaml``.  If no file exists, proceeds with
    empty file_values and relies on CLI overrides.

    Raises ``TypeError`` if required fields (operator, workspace) are still
    missing after merging file + overrides.
    """
    overrides = overrides or {}

    if workspace is not None:
        validate_workspace_name(workspace)

    if config_path is not None:
        # Explicit path — skip workspace resolution
        resolved = config_path if config_path.exists() else None
    elif workspace is not None:
        config_dir = _default_config_dir()
        resolved = _resolve_config_path(config_dir, workspace)
    else:
        config_dir = _default_config_dir()
        resolved = _resolve_config_path(config_dir, workspace=None)

    # Load from YAML if resolved
    file_values: dict = {}
    if resolved is not None and resolved.exists():
        with open(resolved) as f:
            file_values = yaml.safe_load(f) or {}

    # CLI overrides win (skip None values — they mean "not supplied")
    merged = {**file_values}
    for k, v in overrides.items():
        if v is not None:
            merged[k] = v

    valid_keys = {f.name for f in fields(DaemonConfig)}
    filtered = {k: v for k, v in merged.items() if k in valid_keys}

    # DaemonConfig.__init__ will raise TypeError if operator/workspace missing
    return DaemonConfig(**filtered)
