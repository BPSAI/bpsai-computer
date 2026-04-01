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
    poll_interval: int = 5
    process_timeout: int = 1800
    stream_batch_interval: float = 2.0
    stream_buffer_limit: int = 1000

    def __post_init__(self):
        self.poll_interval = int(self.poll_interval)
        self.process_timeout = int(self.process_timeout)
        self.stream_batch_interval = float(self.stream_batch_interval)
        self.stream_buffer_limit = int(self.stream_buffer_limit)


def _default_config_path() -> Path:
    return Path.home() / ".bpsai-computer" / "config.yaml"


def load_config(
    config_path: Path | None = None,
    overrides: dict | None = None,
) -> DaemonConfig:
    """Load config from YAML file, then apply CLI overrides.

    Missing file is OK if overrides supply required fields.
    """
    config_path = config_path or _default_config_path()
    overrides = overrides or {}

    # Load from YAML if it exists
    file_values: dict = {}
    if config_path.exists():
        with open(config_path) as f:
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
