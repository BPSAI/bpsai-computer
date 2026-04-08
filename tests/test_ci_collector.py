"""Tests for CI/test summary collector: pytest result parsing, cursor tracking, push."""

import json

import httpx
import pytest
import respx

from computer.ci_collector import CISummaryCollector
from computer.config import DaemonConfig

BASE = "http://localhost:9999"

_TEST_RESULTS_REL = ".paircoder/telemetry/test_results.json"


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
    return tmp_path / "ci_cursors.json"


@pytest.fixture
def collector(config, cursor_path):
    return CISummaryCollector(config=config, cursor_path=cursor_path)


def _create_repo_with_results(workspace_root, name, results):
    """Create a fake repo with .paircoder/telemetry/test_results.json."""
    repo = workspace_root / name
    results_dir = repo / ".paircoder" / "telemetry"
    results_dir.mkdir(parents=True)
    results_file = results_dir / "test_results.json"
    results_file.write_text(json.dumps(results))
    return repo


def _sample_results(passed=10, failed=0, skipped=2, ts="2026-04-08T12:00:00+00:00"):
    return {
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "errors": 0,
        "timestamp": ts,
        "duration_seconds": 5.2,
    }


class TestRepoDiscovery:
    """AC: Discover repos with test results."""

    def test_discovers_repos_with_results(self, collector):
        ws = collector._workspace_root
        ws.mkdir(parents=True)
        _create_repo_with_results(ws, "repo-a", _sample_results())
        _create_repo_with_results(ws, "repo-b", _sample_results())
        (ws / "repo-c").mkdir()  # no test results

        repos = collector.discover_repos()
        names = {r.name for r in repos}
        assert names == {"repo-a", "repo-b"}

    def test_empty_workspace(self, collector):
        collector._workspace_root.mkdir(parents=True)
        assert collector.discover_repos() == []

    def test_nonexistent_workspace(self, collector):
        assert collector.discover_repos() == []


class TestResultParsing:
    """AC: CI/test summary collected per repo with pass/fail/skip counts."""

    def test_parses_test_results(self, collector):
        ws = collector._workspace_root
        ws.mkdir(parents=True)
        repo = _create_repo_with_results(ws, "repo-a", _sample_results(passed=8, failed=1, skipped=3))

        summary = collector.collect_summary(repo)
        assert summary is not None
        assert summary["passed"] == 8
        assert summary["failed"] == 1
        assert summary["skipped"] == 3
        assert summary["errors"] == 0
        assert summary["timestamp"] == "2026-04-08T12:00:00+00:00"

    def test_no_results_file_returns_none(self, collector):
        ws = collector._workspace_root
        ws.mkdir(parents=True)
        repo = ws / "repo-a"
        repo.mkdir()

        assert collector.collect_summary(repo) is None

    def test_malformed_json_returns_none(self, collector):
        ws = collector._workspace_root
        ws.mkdir(parents=True)
        repo = ws / "repo-a"
        results_dir = repo / ".paircoder" / "telemetry"
        results_dir.mkdir(parents=True)
        (results_dir / "test_results.json").write_text("not json{{{")

        assert collector.collect_summary(repo) is None

    def test_same_timestamp_returns_none(self, collector):
        """If results haven't changed since last push, skip."""
        ws = collector._workspace_root
        ws.mkdir(parents=True)
        ts = "2026-04-08T12:00:00+00:00"
        repo = _create_repo_with_results(ws, "repo-a", _sample_results(ts=ts))

        collector.set_cursor(str(repo), ts)
        assert collector.collect_summary(repo) is None

    def test_new_timestamp_returns_summary(self, collector):
        """New results since last push should be reported."""
        ws = collector._workspace_root
        ws.mkdir(parents=True)
        repo = _create_repo_with_results(
            ws, "repo-a", _sample_results(ts="2026-04-08T13:00:00+00:00"),
        )

        collector.set_cursor(str(repo), "2026-04-08T12:00:00+00:00")
        summary = collector.collect_summary(repo)
        assert summary is not None


class TestPushToA2A:
    """AC: Summary POSTed to /signals with signal_type: ci_summary."""

    @respx.mock
    async def test_push_posts_ci_summary(self, collector, config):
        ws = collector._workspace_root
        ws.mkdir(parents=True)
        _create_repo_with_results(ws, "repo-a", _sample_results(passed=10, failed=1))

        route = respx.post(f"{BASE}/signals").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        await collector.push_summaries()

        assert route.called
        body = json.loads(route.calls[0].request.content)
        assert body["operator"] == "mike"
        assert body["repo"] == "repo-a"
        assert len(body["signals"]) == 1
        sig = body["signals"][0]
        assert sig["signal_type"] == "ci_summary"
        assert sig["severity"] == "info"
        assert sig["payload"]["passed"] == 10
        assert sig["payload"]["failed"] == 1

    @respx.mock
    async def test_cursor_advanced_on_success(self, collector, config, cursor_path):
        ws = collector._workspace_root
        ws.mkdir(parents=True)
        ts = "2026-04-08T12:00:00+00:00"
        repo = _create_repo_with_results(ws, "repo-a", _sample_results(ts=ts))

        respx.post(f"{BASE}/signals").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        await collector.push_summaries()

        assert collector.get_cursor(str(repo)) == ts

    @respx.mock
    async def test_no_summary_skips_push(self, collector, config):
        ws = collector._workspace_root
        ws.mkdir(parents=True)
        ts = "2026-04-08T12:00:00+00:00"
        _create_repo_with_results(ws, "repo-a", _sample_results(ts=ts))
        # Set cursor to same timestamp
        collector.set_cursor(
            str(collector._workspace_root / "repo-a"), ts,
        )

        route = respx.post(f"{BASE}/signals").mock(
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
        _create_repo_with_results(ws, "repo-a", _sample_results())

        respx.post(f"{BASE}/signals").mock(
            return_value=httpx.Response(500, text="error")
        )
        await collector.push_summaries()  # should not raise

    @respx.mock
    async def test_cursor_not_advanced_on_failure(self, collector, config):
        ws = collector._workspace_root
        ws.mkdir(parents=True)
        repo = _create_repo_with_results(ws, "repo-a", _sample_results())

        respx.post(f"{BASE}/signals").mock(
            return_value=httpx.Response(500, text="error")
        )
        await collector.push_summaries()

        assert collector.get_cursor(str(repo)) is None

    @respx.mock
    async def test_network_error_does_not_raise(self, collector, config):
        ws = collector._workspace_root
        ws.mkdir(parents=True)
        _create_repo_with_results(ws, "repo-a", _sample_results())

        respx.post(f"{BASE}/signals").mock(side_effect=httpx.ConnectError("refused"))
        await collector.push_summaries()  # should not raise
