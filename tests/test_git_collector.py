"""Tests for git summary collector: commit counting, branch state, cursor tracking, push."""

import json
from datetime import datetime, timezone
from unittest.mock import patch

import httpx
import pytest
import respx

from computer.config import DaemonConfig
from computer.git_collector import GitSummaryCollector

BASE = "http://localhost:9999"


@pytest.fixture
def config(tmp_path):
    return DaemonConfig(
        operator="mike",
        workspace="bpsai",
        workspace_root=str(tmp_path / "workspace"),
        a2a_url=BASE,
        poll_interval=1,
        process_timeout=30,
    )


@pytest.fixture
def cursor_path(tmp_path):
    return tmp_path / "git_cursors.json"


@pytest.fixture
def collector(config, cursor_path):
    return GitSummaryCollector(config=config, cursor_path=cursor_path)


def _make_git_repo(workspace_root, name):
    """Create a directory with a .git folder to simulate a git repo."""
    repo = workspace_root / name
    (repo / ".git").mkdir(parents=True)
    return repo


class TestRepoDiscovery:
    """AC: Discover git repos in workspace."""

    def test_discovers_git_repos(self, collector):
        ws = collector._workspace_root
        ws.mkdir(parents=True)
        _make_git_repo(ws, "repo-a")
        _make_git_repo(ws, "repo-b")
        # Not a git repo
        (ws / "not-a-repo").mkdir()

        repos = collector.discover_repos()
        names = {r.name for r in repos}
        assert names == {"repo-a", "repo-b"}

    def test_discovers_nested_git_repos(self, collector):
        ws = collector._workspace_root
        ws.mkdir(parents=True)
        _make_git_repo(ws / "org", "nested-repo")

        repos = collector.discover_repos()
        assert len(repos) == 1
        assert repos[0].name == "nested-repo"

    def test_empty_workspace(self, collector):
        collector._workspace_root.mkdir(parents=True)
        assert collector.discover_repos() == []

    def test_nonexistent_workspace(self, collector):
        assert collector.discover_repos() == []


class TestCursorTracking:
    """AC: Cursor state tracks last-pushed git commit SHA per repo."""

    def test_initial_cursor_is_none(self, collector):
        assert collector.get_cursor("/some/repo") is None

    def test_save_and_load(self, collector, cursor_path):
        collector.set_cursor("/repo/a", "abc123")
        collector.save_cursors()

        assert cursor_path.exists()
        data = json.loads(cursor_path.read_text())
        assert data["/repo/a"] == "abc123"

    def test_load_persisted(self, config, cursor_path):
        cursor_path.write_text(json.dumps({"/repo/a": "sha1", "/repo/b": "sha2"}))
        c = GitSummaryCollector(config=config, cursor_path=cursor_path)
        assert c.get_cursor("/repo/a") == "sha1"
        assert c.get_cursor("/repo/b") == "sha2"

    def test_missing_file_starts_fresh(self, collector):
        assert collector.get_cursor("/any") is None


class TestGitSummaryCollection:
    """AC: Git summary collected per repo with commit count, authors, ahead/behind."""

    def test_collects_commits_since_cursor(self, collector):
        """Commit count and authors since last-pushed SHA."""
        with patch.object(collector, "_git") as mock_git:
            mock_git.side_effect = lambda repo, *args: {
                ("rev-parse", "HEAD"): "def456",
                ("rev-parse", "--abbrev-ref", "HEAD"): "feature/x",
                ("log", "--oneline", "abc123..HEAD"): "def456 commit 2\nghi789 commit 1",
                ("log", "--format=%an", "abc123..HEAD"): "Alice\nBob\nAlice",
                ("rev-list", "--left-right", "--count", "@{upstream}...HEAD"): "1\t3",
                ("branch", "-r"): "  origin/main\n  origin/feature/pr-1\n  origin/feature/pr-2",
            }.get(args)

            collector.set_cursor(str(collector._workspace_root / "repo"), "abc123")
            summary = collector.collect_summary(collector._workspace_root / "repo")

        assert summary is not None
        assert summary["commit_count"] == 2
        assert set(summary["authors"]) == {"Alice", "Bob"}
        assert summary["branch"] == "feature/x"
        assert summary["ahead"] == 3
        assert summary["behind"] == 1

    def test_no_new_commits_returns_none(self, collector):
        """If HEAD == cursor SHA, nothing to report."""
        with patch.object(collector, "_git") as mock_git:
            mock_git.side_effect = lambda repo, *args: {
                ("rev-parse", "HEAD"): "abc123",
            }.get(args)

        collector.set_cursor(str(collector._workspace_root / "repo"), "abc123")
        summary = collector.collect_summary(collector._workspace_root / "repo")
        assert summary is None

    def test_first_time_no_cursor(self, collector):
        """First collection with no prior cursor — reports recent commits."""
        with patch.object(collector, "_git") as mock_git:
            mock_git.side_effect = lambda repo, *args: {
                ("rev-parse", "HEAD"): "abc123",
                ("rev-parse", "--abbrev-ref", "HEAD"): "main",
                ("log", "--oneline", "-20"): "abc123 initial commit",
                ("log", "--format=%an", "-20"): "Alice",
                ("rev-list", "--left-right", "--count", "@{upstream}...HEAD"): None,
                ("branch", "-r"): None,
            }.get(args)

            summary = collector.collect_summary(collector._workspace_root / "repo")

        assert summary is not None
        assert summary["commit_count"] == 1
        assert summary["authors"] == ["Alice"]
        assert summary["ahead"] == 0
        assert summary["behind"] == 0
        assert summary["open_pr_branches"] == 0

    def test_git_failure_returns_none(self, collector):
        """If git rev-parse HEAD fails, skip the repo."""
        with patch.object(collector, "_git", return_value=None):
            summary = collector.collect_summary(collector._workspace_root / "repo")
        assert summary is None


class TestRemoteBranchCounting:
    """AC: Open PR count collected via local branch tracking."""

    def test_counts_non_default_remote_branches(self, collector):
        output = (
            "  origin/HEAD -> origin/main\n"
            "  origin/main\n"
            "  origin/dev\n"
            "  origin/feature/login\n"
            "  origin/feature/signup\n"
            "  origin/fix/typo\n"
        )
        count = collector._count_remote_branches(output)
        assert count == 3  # login, signup, typo

    def test_no_remote_branches(self, collector):
        assert collector._count_remote_branches(None) == 0
        assert collector._count_remote_branches("") == 0

    def test_only_default_branches(self, collector):
        output = "  origin/main\n  origin/master\n  origin/dev\n"
        assert collector._count_remote_branches(output) == 0


class TestPushToA2A:
    """AC: Summary POSTed to /signals with signal_type: git_summary."""

    @respx.mock
    async def test_push_posts_git_summary(self, collector, config):
        ws = collector._workspace_root
        ws.mkdir(parents=True)
        _make_git_repo(ws, "repo-a")

        summary = {
            "head_sha": "def456",
            "commit_count": 2,
            "authors": ["Alice"],
            "branch": "main",
            "ahead": 0,
            "behind": 0,
            "open_pr_branches": 1,
        }
        with patch.object(collector, "collect_summary", return_value=summary):
            route = respx.post(f"{BASE}/signals/batch").mock(
                return_value=httpx.Response(200, json={"ok": True})
            )
            await collector.push_summaries()

        assert route.called
        body = json.loads(route.calls[0].request.content)
        assert body["operator"] == "mike"
        assert body["repo"] == "repo-a"
        assert len(body["signals"]) == 1
        sig = body["signals"][0]
        assert sig["signal_type"] == "git_summary"
        assert sig["severity"] == "info"
        assert sig["payload"]["commit_count"] == 2
        # signal_id present and non-empty
        assert isinstance(sig["signal_id"], str)
        assert len(sig["signal_id"]) > 0
        # Timestamp in canonical UTC format (no microseconds, Z suffix)
        assert sig["timestamp"].endswith("Z")
        assert "+" not in sig["timestamp"]

    @respx.mock
    async def test_auth_headers_sent_when_token_manager_set(self, config, cursor_path):
        """POST includes Authorization header when token_manager is provided."""
        from unittest.mock import AsyncMock

        mock_tm = AsyncMock()
        mock_tm.get_token = AsyncMock(return_value="test-jwt-token")
        collector = GitSummaryCollector(config=config, cursor_path=cursor_path, token_manager=mock_tm)

        ws = collector._workspace_root
        ws.mkdir(parents=True)
        _make_git_repo(ws, "repo-a")

        summary = {"head_sha": "abc", "commit_count": 1, "authors": [], "branch": "main", "ahead": 0, "behind": 0, "open_pr_branches": 0}
        with patch.object(collector, "collect_summary", return_value=summary):
            route = respx.post(f"{BASE}/signals/batch").mock(
                return_value=httpx.Response(200, json={"ok": True})
            )
            await collector.push_summaries()

        assert route.called
        auth = route.calls[0].request.headers.get("authorization")
        assert auth == "Bearer test-jwt-token"

    @respx.mock
    async def test_cursor_advanced_on_success(self, collector, config, cursor_path):
        ws = collector._workspace_root
        ws.mkdir(parents=True)
        repo = _make_git_repo(ws, "repo-a")

        summary = {"head_sha": "newsha", "commit_count": 1, "authors": [], "branch": "main", "ahead": 0, "behind": 0, "open_pr_branches": 0}
        with patch.object(collector, "collect_summary", return_value=summary):
            respx.post(f"{BASE}/signals/batch").mock(
                return_value=httpx.Response(200, json={"ok": True})
            )
            await collector.push_summaries()

        assert collector.get_cursor(str(repo)) == "newsha"

    @respx.mock
    async def test_no_summary_skips_push(self, collector, config):
        ws = collector._workspace_root
        ws.mkdir(parents=True)
        _make_git_repo(ws, "repo-a")

        with patch.object(collector, "collect_summary", return_value=None):
            route = respx.post(f"{BASE}/signals/batch").mock(
                return_value=httpx.Response(200, json={"ok": True})
            )
            await collector.push_summaries()

        assert not route.called


class TestPushResilience:
    """AC: Fire-and-forget — push failure does not block daemon."""

    @respx.mock
    async def test_push_failure_does_not_raise(self, collector, config):
        ws = collector._workspace_root
        ws.mkdir(parents=True)
        _make_git_repo(ws, "repo-a")

        summary = {"head_sha": "sha1", "commit_count": 1, "authors": [], "branch": "main", "ahead": 0, "behind": 0, "open_pr_branches": 0}
        with patch.object(collector, "collect_summary", return_value=summary):
            respx.post(f"{BASE}/signals/batch").mock(
                return_value=httpx.Response(500, text="error")
            )
            await collector.push_summaries()  # should not raise

    @respx.mock
    async def test_cursor_not_advanced_on_failure(self, collector, config):
        ws = collector._workspace_root
        ws.mkdir(parents=True)
        repo = _make_git_repo(ws, "repo-a")

        summary = {"head_sha": "sha1", "commit_count": 1, "authors": [], "branch": "main", "ahead": 0, "behind": 0, "open_pr_branches": 0}
        with patch.object(collector, "collect_summary", return_value=summary):
            respx.post(f"{BASE}/signals/batch").mock(
                return_value=httpx.Response(500, text="error")
            )
            await collector.push_summaries()

        assert collector.get_cursor(str(repo)) is None

    @respx.mock
    async def test_network_error_does_not_raise(self, collector, config):
        ws = collector._workspace_root
        ws.mkdir(parents=True)
        _make_git_repo(ws, "repo-a")

        summary = {"head_sha": "sha1", "commit_count": 1, "authors": [], "branch": "main", "ahead": 0, "behind": 0, "open_pr_branches": 0}
        with patch.object(collector, "collect_summary", return_value=summary):
            respx.post(f"{BASE}/signals/batch").mock(side_effect=httpx.ConnectError("refused"))
            await collector.push_summaries()  # should not raise
