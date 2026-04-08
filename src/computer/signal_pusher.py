"""Signal pusher: read signals.jsonl from workspace repos, push to A2A."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from computer.config import DaemonConfig

log = logging.getLogger(__name__)

_SIGNALS_REL = Path(".paircoder") / "telemetry" / "signals.jsonl"


class SignalPusher:
    """Discovers repos with signals.jsonl, pushes new signals to A2A /signals."""

    def __init__(
        self,
        config: DaemonConfig,
        cursor_path: Path | None = None,
    ) -> None:
        self._config = config
        self._workspace_root = Path(config.workspace_root)
        self._cursor_path = cursor_path or (
            Path.home() / ".bpsai-computer" / "signal_cursors.json"
        )
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

    def discover_repos(self) -> list[Path]:
        if not self._workspace_root.exists():
            return []
        repos = []
        for child in sorted(self._workspace_root.iterdir()):
            if child.is_dir() and (child / _SIGNALS_REL).exists():
                repos.append(child)
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
        return {
            "operator": self._config.operator,
            "repo": repo_name,
            "signals": [
                {
                    "signal_type": s.get("signal_type", ""),
                    "severity": s.get("severity", ""),
                    "timestamp": s.get("timestamp", ""),
                    "payload": s.get("payload", {}),
                    "source": s.get("source", ""),
                }
                for s in signals
            ],
        }

    async def push_signals(self) -> None:
        repos = self.discover_repos()
        for repo in repos:
            signals = self.read_new_signals(repo)
            if not signals:
                continue
            batch = self.build_batch(repo_name=repo.name, signals=signals)
            try:
                resp = await self._http.post(
                    f"{self._config.a2a_url}/signals",
                    json=batch,
                )
                resp.raise_for_status()
            except (httpx.HTTPStatusError, httpx.HTTPError) as exc:
                log.warning("Signal push failed for %s: %s", repo.name, exc)
                continue
            # Advance cursor only on success
            signals_file = repo / _SIGNALS_REL
            total_lines = len(signals_file.read_text().splitlines())
            self.set_cursor(str(repo), total_lines)
        self.save_cursors()

    async def close(self) -> None:
        await self._http.aclose()
