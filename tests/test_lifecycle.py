"""Tests for session lifecycle messages (CD2.2)."""

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx

from computer.a2a_client import A2AClient
from computer.config import DaemonConfig
from computer.lifecycle import SessionLifecycle, extract_session_id


BASE = "http://localhost:9999"


@pytest.fixture
def config(tmp_path):
    return DaemonConfig(
        operator="mike",
        workspace="bpsai",
        workspace_root=str(tmp_path),
        a2a_url=BASE,
        poll_interval=1,
        process_timeout=10,
        license_id="lic-test",
    )


@pytest.fixture
def a2a_client():
    return A2AClient(base_url=BASE, operator="mike", workspace="bpsai")


@pytest.fixture
def lifecycle(a2a_client):
    return SessionLifecycle(a2a=a2a_client)


# ── extract_session_id ───────────────────────────────────────────────


class TestExtractSessionId:
    """Extract Claude Code session ID from stdout lines."""

    def test_extracts_session_id_from_output(self):
        lines = [
            "Loading project...",
            "Session: abc-123-def",
            "Ready.",
        ]
        assert extract_session_id(lines) == "abc-123-def"

    def test_extracts_first_session_line(self):
        lines = [
            "Session: first-id",
            "Session: second-id",
        ]
        assert extract_session_id(lines) == "first-id"

    def test_returns_fallback_uuid_when_no_session_line(self):
        lines = ["Hello", "No session here"]
        result = extract_session_id(lines)
        # Should be a valid UUID-like string
        assert len(result) > 0
        assert result != ""

    def test_returns_fallback_uuid_for_empty_output(self):
        result = extract_session_id([])
        assert len(result) > 0

    def test_strips_whitespace_from_session_id(self):
        lines = ["Session:   spaced-id   "]
        assert extract_session_id(lines) == "spaced-id"

    def test_fallback_uuid_is_deterministic_with_seed(self):
        """Fallback uses provided fallback_id if given."""
        result = extract_session_id([], fallback_id="my-fallback")
        assert result == "my-fallback"


# ── A2AClient.post_lifecycle ─────────────────────────────────────────


class TestPostLifecycle:
    """Test posting lifecycle messages via A2AClient."""

    @respx.mock
    async def test_post_lifecycle_sends_correct_payload(self, a2a_client):
        route = respx.post(f"{BASE}/messages").mock(
            return_value=httpx.Response(201, json={"id": "msg-lc-1"})
        )
        await a2a_client.post_lifecycle(
            event_type="session-started",
            session_id="sess-42",
            data={"command": "claude -p 'hello'", "machine": "dev-1"},
        )
        assert route.called
        body = json.loads(route.calls[0].request.content)
        assert body["type"] == "session-started"
        assert body["from_project"] == "bpsai-computer"
        assert body["operator"] == "mike"
        assert body["workspace"] == "bpsai"
        content = json.loads(body["content"])
        assert content["session_id"] == "sess-42"
        assert content["command"] == "claude -p 'hello'"
        assert content["machine"] == "dev-1"

    @respx.mock
    async def test_post_lifecycle_handles_error_gracefully(self, a2a_client):
        respx.post(f"{BASE}/messages").mock(
            return_value=httpx.Response(500, text="fail")
        )
        # Should not raise
        await a2a_client.post_lifecycle(
            event_type="session-started",
            session_id="sess-42",
            data={},
        )


# ── SessionLifecycle ─────────────────────────────────────────────────


class TestSessionLifecycleStart:
    """Test session-started lifecycle event."""

    async def test_post_session_started(self, lifecycle):
        lifecycle._a2a = AsyncMock()
        await lifecycle.post_started(
            session_id="sess-1",
            operator="mike",
            machine="dev-box",
            workspace="bpsai",
            command="claude -p 'audit'",
        )
        lifecycle._a2a.post_lifecycle.assert_called_once()
        call_args = lifecycle._a2a.post_lifecycle.call_args
        assert call_args.kwargs["event_type"] == "session-started"
        assert call_args.kwargs["session_id"] == "sess-1"
        data = call_args.kwargs["data"]
        assert data["operator"] == "mike"
        assert data["machine"] == "dev-box"
        assert data["workspace"] == "bpsai"
        assert data["command"] == "claude -p 'audit'"
        assert "timestamp" in data

    async def test_session_started_includes_timestamp(self, lifecycle):
        lifecycle._a2a = AsyncMock()
        await lifecycle.post_started(
            session_id="s1", operator="o", machine="m",
            workspace="w", command="c",
        )
        data = lifecycle._a2a.post_lifecycle.call_args.kwargs["data"]
        # Timestamp should be ISO format
        assert "T" in data["timestamp"]


class TestSessionLifecycleComplete:
    """Test session-complete lifecycle event."""

    async def test_post_session_complete(self, lifecycle):
        lifecycle._a2a = AsyncMock()
        await lifecycle.post_complete(
            session_id="sess-1",
            exit_code=0,
            duration_seconds=45.2,
            output_summary="Audit complete. No issues.",
        )
        lifecycle._a2a.post_lifecycle.assert_called_once()
        call_args = lifecycle._a2a.post_lifecycle.call_args
        assert call_args.kwargs["event_type"] == "session-complete"
        assert call_args.kwargs["session_id"] == "sess-1"
        data = call_args.kwargs["data"]
        assert data["exit_code"] == 0
        assert data["duration_seconds"] == 45.2
        assert data["output_summary"] == "Audit complete. No issues."
        assert "timestamp" in data

    async def test_output_summary_truncated_to_last_10_lines(self, lifecycle):
        lifecycle._a2a = AsyncMock()
        long_output = "\n".join(f"line {i}" for i in range(20))
        await lifecycle.post_complete(
            session_id="sess-1",
            exit_code=0,
            duration_seconds=10.0,
            output_summary=long_output,
        )
        data = lifecycle._a2a.post_lifecycle.call_args.kwargs["data"]
        summary_lines = data["output_summary"].strip().split("\n")
        assert len(summary_lines) == 10
        assert summary_lines[0] == "line 10"
        assert summary_lines[-1] == "line 19"


class TestSessionLifecycleFailed:
    """Test session-failed lifecycle event."""

    async def test_post_session_failed_crash(self, lifecycle):
        lifecycle._a2a = AsyncMock()
        await lifecycle.post_failed(
            session_id="sess-1",
            error="Segmentation fault",
            exit_code=139,
        )
        lifecycle._a2a.post_lifecycle.assert_called_once()
        call_args = lifecycle._a2a.post_lifecycle.call_args
        assert call_args.kwargs["event_type"] == "session-failed"
        assert call_args.kwargs["session_id"] == "sess-1"
        data = call_args.kwargs["data"]
        assert data["error"] == "Segmentation fault"
        assert data["exit_code"] == 139
        assert "timestamp" in data

    async def test_post_session_failed_timeout(self, lifecycle):
        lifecycle._a2a = AsyncMock()
        await lifecycle.post_failed(
            session_id="sess-1",
            error="Process timeout after 1800s",
            exit_code=None,
        )
        data = lifecycle._a2a.post_lifecycle.call_args.kwargs["data"]
        assert data["error"] == "Process timeout after 1800s"
        assert data["exit_code"] is None


# ── Daemon integration ───────────────────────────────────────────────


class TestDaemonLifecycleIntegration:
    """Test that daemon posts lifecycle events during dispatch."""

    @pytest.fixture
    def daemon(self, config):
        from computer.daemon import Daemon
        d = Daemon(config)
        d.a2a = AsyncMock()
        d.a2a.poll_dispatches = AsyncMock(return_value=[])
        d.a2a.ack_message = AsyncMock()
        d.a2a.post_result = AsyncMock()
        d.a2a.post_lifecycle = AsyncMock()
        d.a2a.post_session_output = AsyncMock()
        d.a2a.heartbeat = AsyncMock()
        return d

    async def test_daemon_posts_session_started_on_dispatch(self, daemon, config, tmp_path):
        """Daemon posts session-started before executing subprocess."""
        repo_dir = tmp_path / "bpsai-a2a"
        repo_dir.mkdir()

        raw_msg = {
            "id": "msg-1",
            "type": "dispatch",
            "content": json.dumps({
                "agent": "driver",
                "target": "bpsai-a2a",
                "prompt": "do work",
            }),
        }

        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(side_effect=[b"Session: cc-sess-42\n", b"done\n", b""])
        mock_stderr = AsyncMock()
        mock_stderr.readline = AsyncMock(side_effect=[b""])

        mock_proc = AsyncMock()
        mock_proc.stdout = mock_stdout
        mock_proc.stderr = mock_stderr
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = 0

        with patch("computer.dispatcher.asyncio.create_subprocess_exec", return_value=mock_proc):
            await daemon._process_dispatch(raw_msg)

        # Check session-started was posted
        lifecycle_calls = [
            c for c in daemon.a2a.post_lifecycle.call_args_list
            if c.kwargs.get("event_type") == "session-started"
            or (c.args and c.args[0] == "session-started")
        ]
        assert len(lifecycle_calls) >= 1

    async def test_daemon_posts_session_complete_on_success(self, daemon, config, tmp_path):
        """Daemon posts session-complete after successful dispatch."""
        repo_dir = tmp_path / "bpsai-a2a"
        repo_dir.mkdir()

        raw_msg = {
            "id": "msg-1",
            "type": "dispatch",
            "content": json.dumps({
                "agent": "driver",
                "target": "bpsai-a2a",
                "prompt": "do work",
            }),
        }

        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(side_effect=[b"output line\n", b""])
        mock_stderr = AsyncMock()
        mock_stderr.readline = AsyncMock(side_effect=[b""])

        mock_proc = AsyncMock()
        mock_proc.stdout = mock_stdout
        mock_proc.stderr = mock_stderr
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = 0

        with patch("computer.dispatcher.asyncio.create_subprocess_exec", return_value=mock_proc):
            await daemon._process_dispatch(raw_msg)

        lifecycle_calls = [
            c for c in daemon.a2a.post_lifecycle.call_args_list
            if c.kwargs.get("event_type") == "session-complete"
            or (c.args and len(c.args) > 0 and c.args[0] == "session-complete")
        ]
        assert len(lifecycle_calls) >= 1

    async def test_daemon_posts_session_failed_on_timeout(self, daemon, config, tmp_path):
        """Daemon posts session-failed on subprocess timeout."""
        repo_dir = tmp_path / "bpsai-a2a"
        repo_dir.mkdir()

        raw_msg = {
            "id": "msg-1",
            "type": "dispatch",
            "content": json.dumps({
                "agent": "driver",
                "target": "bpsai-a2a",
                "prompt": "do work",
            }),
        }

        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(side_effect=TimeoutError)
        mock_stderr = AsyncMock()
        mock_stderr.readline = AsyncMock(side_effect=TimeoutError)

        mock_proc = AsyncMock()
        mock_proc.stdout = mock_stdout
        mock_proc.stderr = mock_stderr
        mock_proc.kill = AsyncMock()
        mock_proc.wait = AsyncMock()

        with patch("computer.dispatcher.asyncio.create_subprocess_exec", return_value=mock_proc):
            await daemon._process_dispatch(raw_msg)

        lifecycle_calls = [
            c for c in daemon.a2a.post_lifecycle.call_args_list
            if c.kwargs.get("event_type") == "session-failed"
            or (c.args and len(c.args) > 0 and c.args[0] == "session-failed")
        ]
        assert len(lifecycle_calls) >= 1

    async def test_daemon_extracts_session_id_from_stdout(self, daemon, config, tmp_path):
        """Daemon extracts Claude Code session ID from stdout."""
        repo_dir = tmp_path / "bpsai-a2a"
        repo_dir.mkdir()

        raw_msg = {
            "id": "msg-1",
            "type": "dispatch",
            "content": json.dumps({
                "agent": "driver",
                "target": "bpsai-a2a",
                "prompt": "do work",
            }),
        }

        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(side_effect=[
            b"Session: cc-real-id-456\n",
            b"output\n",
            b"",
        ])
        mock_stderr = AsyncMock()
        mock_stderr.readline = AsyncMock(side_effect=[b""])

        mock_proc = AsyncMock()
        mock_proc.stdout = mock_stdout
        mock_proc.stderr = mock_stderr
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = 0

        with patch("computer.dispatcher.asyncio.create_subprocess_exec", return_value=mock_proc):
            await daemon._process_dispatch(raw_msg)

        # The session-complete call should use the extracted session ID
        complete_calls = [
            c for c in daemon.a2a.post_lifecycle.call_args_list
            if c.kwargs.get("event_type") == "session-complete"
            or (c.args and len(c.args) > 0 and c.args[0] == "session-complete")
        ]
        assert len(complete_calls) >= 1
        call = complete_calls[0]
        assert call.kwargs["session_id"] == "cc-real-id-456"

    async def test_lifecycle_messages_include_operator_workspace(self, daemon, config, tmp_path):
        """All lifecycle messages are routed with operator/workspace."""
        repo_dir = tmp_path / "bpsai-a2a"
        repo_dir.mkdir()

        raw_msg = {
            "id": "msg-1",
            "type": "dispatch",
            "content": json.dumps({
                "agent": "driver",
                "target": "bpsai-a2a",
                "prompt": "do work",
            }),
        }

        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(side_effect=[b"done\n", b""])
        mock_stderr = AsyncMock()
        mock_stderr.readline = AsyncMock(side_effect=[b""])

        mock_proc = AsyncMock()
        mock_proc.stdout = mock_stdout
        mock_proc.stderr = mock_stderr
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = 0

        with patch("computer.dispatcher.asyncio.create_subprocess_exec", return_value=mock_proc):
            await daemon._process_dispatch(raw_msg)

        # The a2a_client itself has operator/workspace baked in,
        # but the started event data should also contain them
        started_calls = [
            c for c in daemon.a2a.post_lifecycle.call_args_list
            if c.kwargs.get("event_type") == "session-started"
            or (c.args and len(c.args) > 0 and c.args[0] == "session-started")
        ]
        assert len(started_calls) >= 1
        data = started_calls[0].kwargs["data"]
        assert data["operator"] == "mike"
        assert data["workspace"] == "bpsai"
