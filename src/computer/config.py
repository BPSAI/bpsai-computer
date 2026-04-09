"""Daemon configuration: dataclass + YAML loader with CLI overrides."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from pathlib import Path

import yaml


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
    org_id: str | None = None
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
    ``~/.bpsai-computer/config.yaml``.  If neither file exists, raises
    ``FileNotFoundError`` with a helpful message.

    Missing file is OK if overrides supply required fields (only when no
    workspace-based resolution is attempted).
    """
    overrides = overrides or {}

    if config_path is not None:
        # Explicit path — skip workspace resolution
        resolved = config_path if config_path.exists() else None
    elif workspace is not None:
        config_dir = _default_config_dir()
        resolved = _resolve_config_path(config_dir, workspace)
        if resolved is None:
            raise FileNotFoundError(
                f"No config found. Create ~/.bpsai-computer/{workspace}.yaml"
            )
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
