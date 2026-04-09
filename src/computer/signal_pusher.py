"""Signal pusher: read signals.jsonl from workspace repos, push to A2A."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

from computer.scrubber import scrub_credentials

if TYPE_CHECKING:
    from computer.auth import TokenManager
    from computer.config import DaemonConfig

log = logging.getLogger(__name__)

_SIGNALS_REL = Path(".paircoder") / "telemetry" / "signals.jsonl"


def _canonical_ts(ts: str) -> str:
    """Normalize timestamp to YYYY-MM-DDTHH:MM:SSZ (canonical UTC, no microseconds)."""
    if not ts:
        return ts
    from datetime import datetime, timezone

    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            dt = datetime.strptime(ts, fmt)
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue
    return ts


def _make_signal_id(signal_type: str, repo: str, ts: str, payload: dict) -> str:
    """Generate deterministic signal_id from signal content for dedup."""
    content = f"{signal_type}:{repo}:{ts}:{json.dumps(payload, sort_keys=True)}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


class SignalPusher:
    """Discovers repos with signals.jsonl, pushes new signals to A2A /signals."""

    def __init__(
        self,
        config: DaemonConfig,
        cursor_path: Path | None = None,
        token_manager: TokenManager | None = None,
    ) -> None:
        self._config = config
        self._workspace_root = Path(config.workspace_root)
        self._cursor_path = cursor_path or (
            Path.home() / ".bpsai-computer" / config.workspace / "signal_cursors.json"
        )
        self._token_manager = token_manager
        self._cursors: dict[str, int] = self._load_cursors()
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=10.0),
        )

    def _load_cursors(self) -> dict[str, int]:
        if self._cursor_path.exists():
            try:
                return json.loads(self._cursor_path.read_text())
            except (json.JSONDecodeError, OSError):
                log.warning("Failed to load cursor file, starting fresh")
        return {}

    def get_cursor(self, repo_path: str) -> int:
        return self._cursors.get(repo_path, 0)

    def set_cursor(self, repo_path: str, line_number: int) -> None:
        self._cursors[repo_path] = line_number

    def save_cursors(self) -> None:
        self._cursor_path.parent.mkdir(parents=True, exist_ok=True)
        self._cursor_path.write_text(json.dumps(self._cursors, indent=2))

    async def _auth_headers(self) -> dict[str, str]:
        """Return Authorization header if token_manager is configured and token available."""
        if self._token_manager is None:
            return {}
        token = await self._token_manager.get_token()
        if token is None:
            return {}
        return {"Authorization": f"Bearer {token}"}

    def discover_repos(self) -> list[Path]:
        """Find directories under workspace that contain signals.jsonl (any depth)."""
        if not self._workspace_root.exists():
            return []
        _depth = len(_SIGNALS_REL.parts)  # .paircoder / telemetry / signals.jsonl
        repos = sorted({
            p.parents[_depth - 1]
            for p in self._workspace_root.rglob(str(_SIGNALS_REL))
            if p.is_file()
        })
        return repos

    def read_new_signals(self, repo: Path) -> list[dict]:
        signals_file = repo / _SIGNALS_REL
        if not signals_file.exists():
            return []
        cursor = self.get_cursor(str(repo))
        lines = signals_file.read_text().splitlines()
        new_lines = lines[cursor:]
        signals = []
        for line in new_lines:
            line = line.strip()
            if not line:
                continue
            try:
                signals.append(json.loads(line))
            except json.JSONDecodeError:
                log.warning("Skipping malformed signal line in %s", repo.name)
        return signals

    def build_batch(self, repo_name: str, signals: list[dict]) -> dict:
        built = []
        for s in signals:
            ts = _canonical_ts(s.get("timestamp", ""))
            payload = json.loads(
                scrub_credentials(json.dumps(s.get("payload", {})))
            )
            sig_type = s.get("signal_type", "")
            severity = s.get("severity", "")
            signal_id = _make_signal_id(sig_type, repo_name, ts, payload)
            built.append({
                "signal_type": sig_type,
                "severity": severity,
                "timestamp": ts,
                "payload": payload,
                "signal_id": signal_id,
            })
        return {
            "operator": self._config.operator,
            "repo": repo_name,
            "signals": built,
        }

    async def push_signals(self) -> None:
        repos = self.discover_repos()
        for repo in repos:
            signals_file = repo / _SIGNALS_REL
            if not signals_file.exists():
                continue
            cursor = self.get_cursor(str(repo))
            lines = signals_file.read_text().splitlines()
            new_lines = lines[cursor:]
            signals = []
            for line in new_lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    signals.append(json.loads(line))
                except json.JSONDecodeError:
                    log.warning("Skipping malformed signal line in %s", repo.name)
            if not signals:
                continue
            batch = self.build_batch(repo_name=repo.name, signals=signals)
            try:
                headers = await self._auth_headers()
                resp = await self._http.post(
                    f"{self._config.a2a_url}/signals/batch",
                    json=batch,
                    headers=headers,
                )
                resp.raise_for_status()
            except (httpx.HTTPStatusError, httpx.HTTPError) as exc:
                log.warning("Signal push failed for %s: %s", repo.name, exc)
                continue
            # Advance cursor using count from the single read (no TOCTOU)
            self.set_cursor(str(repo), cursor + len(new_lines))
        self.save_cursors()

    async def close(self) -> None:
        await self._http.aclose()
