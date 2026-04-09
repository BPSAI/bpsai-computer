"""Tests for signal pusher: cursor tracking, repo discovery, batch push."""

import json

import httpx
import pytest
import respx

from computer.config import DaemonConfig
from computer.signal_pusher import SignalPusher

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
    return tmp_path / "signal_cursors.json"


@pytest.fixture
def pusher(config, cursor_path):
    return SignalPusher(config=config, cursor_path=cursor_path)


def _make_signal(signal_type="api_failure", severity="warning", ts="2026-03-31T00:00:00+00:00"):
    return json.dumps({
        "signal_type": signal_type,
        "severity": severity,
        "timestamp": ts,
        "session_id": "",
        "payload": {"stop_reason": "subagent_stop"},
        "source": "automated",
    })


def _create_repo_with_signals(workspace_root, repo_name, lines):
    """Create a fake repo dir with .paircoder/telemetry/signals.jsonl."""
    repo = workspace_root / repo_name
    signals_dir = repo / ".paircoder" / "telemetry"
    signals_dir.mkdir(parents=True)
    signals_file = signals_dir / "signals.jsonl"
    signals_file.write_text("\n".join(lines) + "\n" if lines else "")
    return repo


class TestRepoDiscovery:
    """AC: Daemon discovers all repos under workspace_root with signals.jsonl."""

    def test_discovers_repos_with_signals(self, pusher, config):
        ws = pusher._workspace_root
        ws.mkdir(parents=True)
        _create_repo_with_signals(ws, "repo-a", [_make_signal()])
        _create_repo_with_signals(ws, "repo-b", [_make_signal()])
        # repo-c has no signals file
        (ws / "repo-c").mkdir()

        repos = pusher.discover_repos()
        repo_names = {r.name for r in repos}
        assert repo_names == {"repo-a", "repo-b"}

    def test_discovers_nested_repos(self, pusher, config):
        ws = pusher._workspace_root
        ws.mkdir(parents=True)
        _create_repo_with_signals(ws / "org", "nested-repo", [_make_signal()])

        repos = pusher.discover_repos()
        assert len(repos) == 1
        assert repos[0].name == "nested-repo"

    def test_empty_workspace_returns_empty(self, pusher):
        pusher._workspace_root.mkdir(parents=True)
        assert pusher.discover_repos() == []

    def test_nonexistent_workspace_returns_empty(self, pusher):
        # workspace_root doesn't exist yet
        assert pusher.discover_repos() == []


class TestCursorTracking:
    """AC: Cursor state persisted to signal_cursors.json (repo path -> last line number)."""

    def test_initial_cursor_is_zero(self, pusher):
        assert pusher.get_cursor("/some/repo") == 0

    def test_save_and_load_cursor(self, pusher, cursor_path):
        pusher.set_cursor("/some/repo", 5)
        pusher.save_cursors()

        assert cursor_path.exists()
        data = json.loads(cursor_path.read_text())
        assert data["/some/repo"] == 5

    def test_load_persisted_cursors(self, config, cursor_path):
        cursor_path.write_text(json.dumps({"/repo/a": 3, "/repo/b": 7}))
        pusher = SignalPusher(config=config, cursor_path=cursor_path)
        assert pusher.get_cursor("/repo/a") == 3
        assert pusher.get_cursor("/repo/b") == 7

    def test_cursor_survives_missing_file(self, pusher):
        # No file on disk — should start fresh
        assert pusher.get_cursor("/any") == 0


class TestNewSignalDetection:
    """AC: New signals since cursor are read correctly."""

    def test_reads_new_lines_from_cursor(self, pusher, config):
        ws = pusher._workspace_root
        ws.mkdir(parents=True)
        lines = [_make_signal(ts=f"2026-03-31T00:0{i}:00+00:00") for i in range(5)]
        repo = _create_repo_with_signals(ws, "repo-x", lines)

        pusher.set_cursor(str(repo), 2)
        new_signals = pusher.read_new_signals(repo)
        assert len(new_signals) == 3  # lines 2,3,4 (0-indexed)

    def test_no_new_signals_when_cursor_at_end(self, pusher, config):
        ws = pusher._workspace_root
        ws.mkdir(parents=True)
        lines = [_make_signal() for _ in range(3)]
        repo = _create_repo_with_signals(ws, "repo-y", lines)

        pusher.set_cursor(str(repo), 3)
        assert pusher.read_new_signals(repo) == []

    def test_all_signals_when_no_cursor(self, pusher, config):
        ws = pusher._workspace_root
        ws.mkdir(parents=True)
        lines = [_make_signal() for _ in range(4)]
        repo = _create_repo_with_signals(ws, "repo-z", lines)

        new_signals = pusher.read_new_signals(repo)
        assert len(new_signals) == 4


class TestBatchAssembly:
    """AC: Multiple signals per repo bundled into a single POST."""

    def test_batch_payload_structure(self, pusher, config):
        ws = pusher._workspace_root
        ws.mkdir(parents=True)
        lines = [
            _make_signal(ts="2026-03-31T00:01:00+00:00"),
            _make_signal(ts="2026-03-31T00:02:00+00:00"),
        ]
        repo = _create_repo_with_signals(ws, "my-repo", lines)

        signals = pusher.read_new_signals(repo)
        batch = pusher.build_batch(repo_name="my-repo", signals=signals)

        assert batch["operator"] == "mike"
        assert batch["repo"] == "my-repo"
        assert len(batch["signals"]) == 2
        # Timestamps normalized to canonical UTC (no microseconds, Z suffix)
        assert batch["signals"][0]["timestamp"] == "2026-03-31T00:01:00Z"
        # Each signal has a signal_id
        assert "signal_id" in batch["signals"][0]
        assert "signal_id" in batch["signals"][1]
        # signal_ids are strings and non-empty
        assert isinstance(batch["signals"][0]["signal_id"], str)
        assert len(batch["signals"][0]["signal_id"]) > 0

    def test_signal_id_is_deterministic(self, pusher, config):
        """Same signal content produces same signal_id."""
        ws = pusher._workspace_root
        ws.mkdir(parents=True)
        lines = [_make_signal(ts="2026-03-31T00:01:00+00:00")]
        repo = _create_repo_with_signals(ws, "my-repo", lines)

        signals = pusher.read_new_signals(repo)
        batch1 = pusher.build_batch(repo_name="my-repo", signals=signals)
        batch2 = pusher.build_batch(repo_name="my-repo", signals=signals)

        assert batch1["signals"][0]["signal_id"] == batch2["signals"][0]["signal_id"]

    def test_different_signals_get_different_ids(self, pusher, config):
        """Different signal content produces different signal_id."""
        ws = pusher._workspace_root
        ws.mkdir(parents=True)
        lines = [
            _make_signal(ts="2026-03-31T00:01:00+00:00"),
            _make_signal(ts="2026-03-31T00:02:00+00:00"),
        ]
        repo = _create_repo_with_signals(ws, "my-repo", lines)

        signals = pusher.read_new_signals(repo)
        batch = pusher.build_batch(repo_name="my-repo", signals=signals)

        assert batch["signals"][0]["signal_id"] != batch["signals"][1]["signal_id"]

    def test_scrub_credentials_in_payload(self, pusher, config):
        """Credentials in signal payloads are scrubbed before POST."""
        signal = {
            "signal_type": "api_failure",
            "severity": "warning",
            "timestamp": "2026-03-31T00:00:00+00:00",
            "payload": {"api_key": "sk-ant-abc123defghijklmnop"},
            "source": "automated",
        }
        batch = pusher.build_batch(repo_name="test-repo", signals=[signal])

        payload_str = json.dumps(batch["signals"][0]["payload"])
        assert "sk-ant-" not in payload_str
        assert "REDACTED" in payload_str


class TestPushToA2A:
    """AC: Signals POSTed to A2A /signals endpoint with correct fields."""

    @respx.mock
    async def test_push_posts_to_signals_endpoint(self, pusher, config):
        ws = pusher._workspace_root
        ws.mkdir(parents=True)
        lines = [_make_signal()]
        _create_repo_with_signals(ws, "repo-a", lines)

        route = respx.post(f"{BASE}/signals/batch").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        await pusher.push_signals()

        assert route.called
        body = json.loads(route.calls[0].request.content)
        assert body["operator"] == "mike"
        assert body["repo"] == "repo-a"
        assert len(body["signals"]) == 1
        # Verify signal_id present
        assert "signal_id" in body["signals"][0]

    @respx.mock
    async def test_push_updates_cursor_on_success(self, pusher, config, cursor_path):
        ws = pusher._workspace_root
        ws.mkdir(parents=True)
        lines = [_make_signal() for _ in range(3)]
        repo = _create_repo_with_signals(ws, "repo-a", lines)

        respx.post(f"{BASE}/signals/batch").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        await pusher.push_signals()

        assert pusher.get_cursor(str(repo)) == 3
        # Cursor persisted to disk
        assert cursor_path.exists()

    @respx.mock
    async def test_cursor_uses_single_read_no_toctou(self, pusher, config):
        """Cursor advance uses line count from the single read, not a second read_text()."""
        ws = pusher._workspace_root
        ws.mkdir(parents=True)
        lines = [_make_signal() for _ in range(3)]
        repo = _create_repo_with_signals(ws, "repo-a", lines)

        # After the push reads the file, append more lines before POST returns
        original_post = pusher._http.post

        async def post_and_append(*args, **kwargs):
            # Append a line to simulate concurrent write
            signals_file = repo / ".paircoder" / "telemetry" / "signals.jsonl"
            signals_file.write_text(signals_file.read_text() + _make_signal() + "\n")
            return httpx.Response(200, json={"ok": True})

        respx.post(f"{BASE}/signals/batch").mock(side_effect=post_and_append)

        await pusher.push_signals()

        # Cursor should be 3 (from original read), NOT 4 (from re-reading)
        assert pusher.get_cursor(str(repo)) == 3

    @respx.mock
    async def test_auth_headers_sent_when_token_manager_set(self, config, cursor_path):
        """POST includes Authorization header when token_manager is provided."""
        from unittest.mock import AsyncMock

        mock_tm = AsyncMock()
        mock_tm.get_token = AsyncMock(return_value="test-jwt-token")
        pusher = SignalPusher(config=config, cursor_path=cursor_path, token_manager=mock_tm)

        ws = pusher._workspace_root
        ws.mkdir(parents=True)
        _create_repo_with_signals(ws, "repo-a", [_make_signal()])

        route = respx.post(f"{BASE}/signals/batch").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        await pusher.push_signals()

        assert route.called
        auth = route.calls[0].request.headers.get("authorization")
        assert auth == "Bearer test-jwt-token"


class TestPushFailureResilience:
    """AC: Push failure logs warning and continues — does not block dispatch polling."""

    @respx.mock
    async def test_push_failure_logs_and_continues(self, pusher, config, caplog):
        ws = pusher._workspace_root
        ws.mkdir(parents=True)
        _create_repo_with_signals(ws, "repo-a", [_make_signal()])

        respx.post(f"{BASE}/signals/batch").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        # Should not raise
        await pusher.push_signals()
        assert "Signal push failed" in caplog.text

    @respx.mock
    async def test_cursor_not_advanced_on_failure(self, pusher, config):
        ws = pusher._workspace_root
        ws.mkdir(parents=True)
        lines = [_make_signal() for _ in range(3)]
        repo = _create_repo_with_signals(ws, "repo-a", lines)

        respx.post(f"{BASE}/signals/batch").mock(
            return_value=httpx.Response(500, text="error")
        )

        await pusher.push_signals()
        # Cursor should NOT have advanced
        assert pusher.get_cursor(str(repo)) == 0

    @respx.mock
    async def test_network_error_does_not_raise(self, pusher, config):
        ws = pusher._workspace_root
        ws.mkdir(parents=True)
        _create_repo_with_signals(ws, "repo-a", [_make_signal()])

        respx.post(f"{BASE}/signals/batch").mock(side_effect=httpx.ConnectError("refused"))

        # Should not raise
        await pusher.push_signals()

    @respx.mock
    async def test_partial_failure_advances_successful_repos(self, pusher, config):
        """If repo-a succeeds but repo-b fails, only repo-a cursor advances."""
        ws = pusher._workspace_root
        ws.mkdir(parents=True)
        repo_a = _create_repo_with_signals(ws, "repo-a", [_make_signal()])
        repo_b = _create_repo_with_signals(ws, "repo-b", [_make_signal()])

        call_count = 0

        def side_effect(request):
            nonlocal call_count
            call_count += 1
            body = json.loads(request.content)
            if body["repo"] == "repo-a":
                return httpx.Response(200, json={"ok": True})
            return httpx.Response(500, text="error")

        respx.post(f"{BASE}/signals/batch").mock(side_effect=side_effect)

        await pusher.push_signals()

        assert pusher.get_cursor(str(repo_a)) == 1
        assert pusher.get_cursor(str(repo_b)) == 0
