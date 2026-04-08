"""Auto-discover license_id from license.json on disk."""

from __future__ import annotations

import json
import os
from pathlib import Path


class LicenseDiscoveryError(Exception):
    """Raised when license_id cannot be discovered."""


def _resolve_license_path(home_dir: Path | None = None) -> Path:
    """Return the license.json path, checking BPSAI_LICENSE_FILE env var first."""
    env_path = os.environ.get("BPSAI_LICENSE_FILE")
    if env_path:
        return Path(env_path)
    home = home_dir or Path.home()
    return home / ".paircoder" / "license.json"


def discover_license_id(home_dir: Path | None = None) -> str:
    """Find and read license.json, returning payload.license_id.

    Search order:
      1. ``BPSAI_LICENSE_FILE`` env var (explicit path)
      2. ``~/.paircoder/license.json``

    Raises ``LicenseDiscoveryError`` with an actionable message on failure.
    """
    license_path = _resolve_license_path(home_dir)

    if not license_path.exists():
        raise LicenseDiscoveryError(
            f"No license found at {license_path}. "
            "Run: bpsai-pair license install <file>"
        )

    try:
        data = json.loads(license_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise LicenseDiscoveryError(
            f"Failed to read license file {license_path}: {exc}"
        ) from exc

    try:
        license_id = data["payload"]["license_id"]
    except (KeyError, TypeError) as exc:
        raise LicenseDiscoveryError(
            f"Missing payload.license_id in {license_path}: {exc}"
        ) from exc

    return license_id
