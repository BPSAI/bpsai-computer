"""CI/test summary collector: parse pytest results, push to A2A."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from computer.auth import TokenManager
    from computer.config import DaemonConfig

log = logging.getLogger(__name__)

_RESULTS_REL = Path(".paircoder") / "telemetry" / "test_results.json"


def _make_signal_id(signal_type: str, repo: str, ts: str, payload: dict) -> str:
    """Generate deterministic signal_id from signal content for dedup."""
    content = f"{signal_type}:{repo}:{ts}:{json.dumps(payload, sort_keys=True)}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


class CISummaryCollector:
    """Collects CI/test results per workspace repo, pushes as ci_summary signals."""

    def __init__(
        self,
        config: DaemonConfig,
        cursor_path: Path | None = None,
        token_manager: TokenManager | None = None,
    ) -> None:
        self._config = config
        self._workspace_root = Path(config.workspace_root)
        self._cursor_path = cursor_path or (
            Path.home() / ".bpsai-computer" / config.workspace / "ci_cursors.json"
        )
        self._token_manager = token_manager
        self._cursors: dict[str, str] = self._load_cursors()
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=10.0),
        )

    def _load_cursors(self) -> dict[str, str]:
        if self._cursor_path.exists():
            try:
                return json.loads(self._cursor_path.read_text())
            except (json.JSONDecodeError, OSError):
                log.warning("Failed to load CI cursor file, starting fresh")
        return {}

    def get_cursor(self, repo_path: str) -> str | None:
        return self._cursors.get(repo_path)

    def set_cursor(self, repo_path: str, timestamp: str) -> None:
        self._cursors[repo_path] = timestamp

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
        """Find directories under workspace that have test_results.json (any depth)."""
        if not self._workspace_root.exists():
            return []
        _depth = len(_RESULTS_REL.parts)  # .paircoder / telemetry / test_results.json
        repos = sorted({
            p.parents[_depth - 1]
            for p in self._workspace_root.rglob(str(_RESULTS_REL))
            if p.is_file()
        })
        return repos

    def collect_summary(self, repo: Path) -> dict | None:
        """Read test_results.json, return summary or None if unchanged."""
        results_file = repo / _RESULTS_REL
        if not results_file.exists():
            return None
        try:
            data = json.loads(results_file.read_text())
        except (json.JSONDecodeError, OSError):
            log.warning("Malformed test_results.json in %s", repo.name)
            return None

        ts = data.get("timestamp", "")
        last_ts = self.get_cursor(str(repo))
        if ts and ts == last_ts:
            return None

        return {
            "passed": data.get("passed", 0),
            "failed": data.get("failed", 0),
            "skipped": data.get("skipped", 0),
            "errors": data.get("errors", 0),
            "timestamp": ts,
            "duration_seconds": data.get("duration_seconds", 0),
        }

    async def push_summaries(self) -> None:
        """Collect and push CI summaries for all discovered repos."""
        repos = self.discover_repos()
        for repo in repos:
            summary = self.collect_summary(repo)
            if not summary:
                continue
            result_ts = summary["timestamp"]
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            sig_type = "ci_summary"
            signal_id = _make_signal_id(sig_type, repo.name, ts, summary)
            batch = {
                "operator": self._config.operator,
                "repo": repo.name,
                "signals": [{
                    "signal_type": sig_type,
                    "severity": "info",
                    "timestamp": ts,
                    "payload": summary,
                    "signal_id": signal_id,
                }],
            }
            try:
                headers = await self._auth_headers()
                resp = await self._http.post(
                    f"{self._config.a2a_url}/signals/batch", json=batch, headers=headers,
                )
                resp.raise_for_status()
            except (httpx.HTTPStatusError, httpx.HTTPError) as exc:
                log.warning("CI summary push failed for %s: %s", repo.name, exc)
                continue
            self.set_cursor(str(repo), result_ts)
        self.save_cursors()

    async def close(self) -> None:
        await self._http.aclose()
