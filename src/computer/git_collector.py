"""Git summary collector: collect commit/branch state per repo, push to A2A."""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from computer.auth import TokenManager
    from computer.config import DaemonConfig

log = logging.getLogger(__name__)


def _make_signal_id(signal_type: str, repo: str, ts: str, payload: dict) -> str:
    """Generate deterministic signal_id from signal content for dedup."""
    content = f"{signal_type}:{repo}:{ts}:{json.dumps(payload, sort_keys=True)}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


class GitSummaryCollector:
    """Collects git summary per workspace repo, pushes to A2A as git_summary signals."""

    def __init__(
        self,
        config: DaemonConfig,
        cursor_path: Path | None = None,
        token_manager: TokenManager | None = None,
    ) -> None:
        self._config = config
        self._workspace_root = Path(config.workspace_root)
        self._cursor_path = cursor_path or (
            Path.home() / ".bpsai-computer" / config.workspace / "git_cursors.json"
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
                log.warning("Failed to load git cursor file, starting fresh")
        return {}

    def get_cursor(self, repo_path: str) -> str | None:
        return self._cursors.get(repo_path)

    def set_cursor(self, repo_path: str, sha: str) -> None:
        self._cursors[repo_path] = sha

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
        """Find directories under workspace that contain a .git folder (any depth)."""
        if not self._workspace_root.exists():
            return []
        repos = sorted(
            {p.parent for p in self._workspace_root.rglob(".git") if p.is_dir()}
        )
        return repos

    def _git(self, repo: Path, *args: str) -> str | None:
        """Run a git command in repo, return stdout or None on error.

        Security: *args* are passed directly to ``subprocess.run`` and must
        come from trusted, hard-coded values — never from user or network input.
        """
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=str(repo),
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return None
            return result.stdout.strip()
        except (subprocess.TimeoutExpired, OSError):
            return None

    def collect_summary(self, repo: Path) -> dict | None:
        """Collect git summary for a repo. Returns None if no new commits."""
        head_sha = self._git(repo, "rev-parse", "HEAD")
        if not head_sha:
            return None

        last_sha = self.get_cursor(str(repo))
        if head_sha == last_sha:
            return None

        if last_sha:
            log_out = self._git(repo, "log", "--oneline", f"{last_sha}..HEAD")
            authors_out = self._git(repo, "log", "--format=%an", f"{last_sha}..HEAD")
        else:
            log_out = self._git(repo, "log", "--oneline", "-20")
            authors_out = self._git(repo, "log", "--format=%an", "-20")

        commits = log_out.strip().splitlines() if log_out else []
        authors = list(set(authors_out.strip().splitlines())) if authors_out else []

        branch = self._git(repo, "rev-parse", "--abbrev-ref", "HEAD") or "unknown"
        ahead, behind = self._get_ahead_behind(repo)
        remote_out = self._git(repo, "branch", "-r")
        open_prs = self._count_remote_branches(remote_out)

        return {
            "head_sha": head_sha,
            "commit_count": len(commits),
            "authors": authors,
            "branch": branch,
            "ahead": ahead,
            "behind": behind,
            "open_pr_branches": open_prs,
        }

    def _get_ahead_behind(self, repo: Path) -> tuple[int, int]:
        """Get ahead/behind count relative to upstream tracking branch."""
        output = self._git(repo, "rev-list", "--left-right", "--count", "@{upstream}...HEAD")
        if not output:
            return 0, 0
        parts = output.strip().split()
        if len(parts) == 2:
            return int(parts[1]), int(parts[0])
        return 0, 0

    def _count_remote_branches(self, output: str | None) -> int:
        """Count remote branches excluding main/master/dev/HEAD."""
        if not output:
            return 0
        exclude = {"main", "master", "dev", "HEAD"}
        count = 0
        for line in output.strip().splitlines():
            line = line.strip()
            if "->" in line:
                continue
            branch_name = line.split("/")[-1] if "/" in line else line
            if branch_name not in exclude:
                count += 1
        return count

    async def push_summaries(self) -> None:
        """Collect and push git summaries for all discovered repos."""
        repos = self.discover_repos()
        for repo in repos:
            summary = self.collect_summary(repo)
            if not summary:
                continue
            head_sha = summary.pop("head_sha")
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            sig_type = "git_summary"
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
                log.warning("Git summary push failed for %s: %s", repo.name, exc)
                continue
            self.set_cursor(str(repo), head_sha)
        self.save_cursors()

    async def close(self) -> None:
        await self._http.aclose()
