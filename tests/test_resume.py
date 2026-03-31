"""Tests for resume command handler (CD2.3)."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from computer.config import DaemonConfig
from computer.dispatcher import (
    DispatchExecutor,
    ResumeMessage,
    parse_resume,
)


@pytest.fixture
def config(tmp_path):
    return DaemonConfig(
        operator="mike",
        workspace="bpsai",
        workspace_root=str(tmp_path),
        a2a_url="http://localhost:9999",
        poll_interval=1,
        process_timeout=10,
    )


@pytest.fixture
def executor(config):
    return DispatchExecutor(config)


# ── parse_resume ────────────────────────────────────────────────────


class TestParseResume:
    """Test parsing resume messages from A2A."""

    def test_parse_resume_structured(self):
        raw = {
            "id": "msg-r1",
            "type": "resume",
            "operator": "mike",
            "content": json.dumps({
                "session_id": "sess-abc-123",
                "target": "bpsai-a2a",
            }),
        }
        msg = parse_resume(raw)
        assert isinstance(msg, ResumeMessage)
        assert msg.message_id == "msg-r1"
        assert msg.session_id == "sess-abc-123"
        assert msg.target == "bpsai-a2a"

    def test_parse_resume_missing_session_id_raises(self):
        raw = {
            "id": "msg-r2",
            "type": "resume",
            "content": json.dumps({"target": "bpsai-a2a"}),
        }
        with pytest.raises((KeyError, ValueError)):
            parse_resume(raw)

    def test_parse_resume_invalid_json_raises(self):
        raw = {
            "id": "msg-r3",
            "type": "resume",
            "content": "not json",
        }
        with pytest.raises((json.JSONDecodeError, ValueError, KeyError)):
            parse_resume(raw)

    def test_parse_resume_missing_target_raises(self):
        raw = {
            "id": "msg-r4",
            "type": "resume",
            "content": json.dumps({"session_id": "sess-1"}),
        }
        with pytest.raises((KeyError, ValueError)):
            parse_resume(raw)


# ── execute_resume ──────────────────────────────────────────────────


class TestExecuteResume:
    """Test executing claude --resume subprocess."""

    async def test_execute_resume_launches_with_resume_flag(self, executor, config, tmp_path):
        """execute_resume spawns claude --resume {session_id}."""
        repo_dir = tmp_path / "bpsai-a2a"
        repo_dir.mkdir()

        msg = ResumeMessage(
            message_id="msg-r1",
            session_id="sess-abc-123",
            target="bpsai-a2a",
        )

        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(side_effect=[b"Resumed session\n", b""])
        mock_stderr = AsyncMock()
        mock_stderr.readline = AsyncMock(side_effect=[b""])

        mock_proc = AsyncMock()
        mock_proc.stdout = mock_stdout
        mock_proc.stderr = mock_stderr
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = 0

        with patch("computer.dispatcher.asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            result = await executor.execute_resume(msg)
            mock_exec.assert_called_once()
            call_args = mock_exec.call_args[0]
            assert "claude" in call_args[0]
            assert "--resume" in call_args
            assert "sess-abc-123" in call_args
            assert "--dangerously-skip-permissions" in call_args
            assert result.success
            assert "Resumed session" in result.output

    async def test_execute_resume_missing_repo_returns_error(self, executor, config):
        msg = ResumeMessage(
            message_id="msg-r1",
            session_id="sess-abc",
            target="nonexistent-repo",
        )
        result = await executor.execute_resume(msg)
        assert not result.success
        assert "not found" in result.output.lower()

    async def test_execute_resume_handles_timeout(self, executor, config, tmp_path):
        repo_dir = tmp_path / "bpsai-a2a"
        repo_dir.mkdir()

        msg = ResumeMessage(
            message_id="msg-r1",
            session_id="sess-abc",
            target="bpsai-a2a",
        )

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
            result = await executor.execute_resume(msg)
            assert not result.success
            assert "timeout" in result.output.lower()

    async def test_execute_resume_handles_nonzero_exit(self, executor, config, tmp_path):
        repo_dir = tmp_path / "bpsai-a2a"
        repo_dir.mkdir()

        msg = ResumeMessage(
            message_id="msg-r1",
            session_id="sess-abc",
            target="bpsai-a2a",
        )

        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(side_effect=[b"partial\n", b""])
        mock_stderr = AsyncMock()
        mock_stderr.readline = AsyncMock(side_effect=[b"session not found\n", b""])

        mock_proc = AsyncMock()
        mock_proc.stdout = mock_stdout
        mock_proc.stderr = mock_stderr
        mock_proc.wait = AsyncMock(return_value=1)
        mock_proc.returncode = 1

        with patch("computer.dispatcher.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await executor.execute_resume(msg)
            assert not result.success
            assert "exit code 1" in result.output.lower()

    async def test_execute_resume_with_streamer(self, executor, config, tmp_path):
        repo_dir = tmp_path / "bpsai-a2a"
        repo_dir.mkdir()

        msg = ResumeMessage(
            message_id="msg-r1",
            session_id="sess-abc",
            target="bpsai-a2a",
        )

        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(side_effect=[b"line one\n", b"line two\n", b""])
        mock_stderr = AsyncMock()
        mock_stderr.readline = AsyncMock(side_effect=[b""])

        mock_proc = AsyncMock()
        mock_proc.stdout = mock_stdout
        mock_proc.stderr = mock_stderr
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = 0

        add_line_calls = []
        streamer = AsyncMock()
        streamer.add_line = lambda content, stream: add_line_calls.append((content, stream))

        with patch("computer.dispatcher.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await executor.execute_resume(msg, streamer=streamer)
            assert result.success
            assert len(add_line_calls) == 2


# ── Daemon resume handling ──────────────────────────────────────────


class TestDaemonResume:
    """Test daemon handling of resume messages."""

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

    async def test_process_resume_posts_lifecycle_started_with_resumed_flag(self, daemon, config, tmp_path):
        """session-started lifecycle includes resumed=true."""
        repo_dir = tmp_path / "bpsai-a2a"
        repo_dir.mkdir()

        raw_msg = {
            "id": "msg-r1",
            "type": "resume",
            "operator": "mike",
            "content": json.dumps({
                "session_id": "sess-to-resume",
                "target": "bpsai-a2a",
            }),
        }

        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(side_effect=[b"Session: cc-resumed-id\n", b"done\n", b""])
        mock_stderr = AsyncMock()
        mock_stderr.readline = AsyncMock(side_effect=[b""])

        mock_proc = AsyncMock()
        mock_proc.stdout = mock_stdout
        mock_proc.stderr = mock_stderr
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = 0

        with patch("computer.dispatcher.asyncio.create_subprocess_exec", return_value=mock_proc):
            await daemon._process_resume(raw_msg)

        started_calls = [
            c for c in daemon.a2a.post_lifecycle.call_args_list
            if c.kwargs.get("event_type") == "session-started"
            or (c.args and c.args[0] == "session-started")
        ]
        assert len(started_calls) >= 1
        data = started_calls[0].kwargs["data"]
        assert data["resumed"] is True

    async def test_process_resume_posts_session_complete(self, daemon, config, tmp_path):
        repo_dir = tmp_path / "bpsai-a2a"
        repo_dir.mkdir()

        raw_msg = {
            "id": "msg-r1",
            "type": "resume",
            "operator": "mike",
            "content": json.dumps({
                "session_id": "sess-to-resume",
                "target": "bpsai-a2a",
            }),
        }

        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(side_effect=[b"output\n", b""])
        mock_stderr = AsyncMock()
        mock_stderr.readline = AsyncMock(side_effect=[b""])

        mock_proc = AsyncMock()
        mock_proc.stdout = mock_stdout
        mock_proc.stderr = mock_stderr
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = 0

        with patch("computer.dispatcher.asyncio.create_subprocess_exec", return_value=mock_proc):
            await daemon._process_resume(raw_msg)

        complete_calls = [
            c for c in daemon.a2a.post_lifecycle.call_args_list
            if c.kwargs.get("event_type") == "session-complete"
            or (c.args and len(c.args) > 0 and c.args[0] == "session-complete")
        ]
        assert len(complete_calls) >= 1

    async def test_process_resume_posts_result(self, daemon, config, tmp_path):
        repo_dir = tmp_path / "bpsai-a2a"
        repo_dir.mkdir()

        raw_msg = {
            "id": "msg-r1",
            "type": "resume",
            "operator": "mike",
            "content": json.dumps({
                "session_id": "sess-to-resume",
                "target": "bpsai-a2a",
            }),
        }

        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(side_effect=[b"resumed output\n", b""])
        mock_stderr = AsyncMock()
        mock_stderr.readline = AsyncMock(side_effect=[b""])

        mock_proc = AsyncMock()
        mock_proc.stdout = mock_stdout
        mock_proc.stderr = mock_stderr
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = 0

        with patch("computer.dispatcher.asyncio.create_subprocess_exec", return_value=mock_proc):
            await daemon._process_resume(raw_msg)

        daemon.a2a.post_result.assert_called_once()

    async def test_process_resume_command_includes_resume_flag(self, daemon, config, tmp_path):
        """The command in session-started should show --resume flag."""
        repo_dir = tmp_path / "bpsai-a2a"
        repo_dir.mkdir()

        raw_msg = {
            "id": "msg-r1",
            "type": "resume",
            "operator": "mike",
            "content": json.dumps({
                "session_id": "sess-to-resume",
                "target": "bpsai-a2a",
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
            await daemon._process_resume(raw_msg)

        started_calls = [
            c for c in daemon.a2a.post_lifecycle.call_args_list
            if c.kwargs.get("event_type") == "session-started"
            or (c.args and c.args[0] == "session-started")
        ]
        data = started_calls[0].kwargs["data"]
        assert "--resume" in data["command"]
        assert "sess-to-resume" in data["command"]


# ── A2A client resume polling ───────────────────────────────────────


class TestPollIncludesResume:
    """Test that poll_dispatches now also returns resume messages."""

    async def test_poll_returns_resume_messages(self):
        import httpx
        import respx

        from computer.a2a_client import A2AClient
        client = A2AClient(base_url="http://localhost:9999", operator="mike", workspace="bpsai")

        messages = [
            {"id": "msg-d1", "type": "dispatch", "content": "{}"},
            {"id": "msg-r1", "type": "resume", "content": "{}"},
        ]
        with respx.mock:
            respx.get("http://localhost:9999/messages/feed").mock(
                return_value=httpx.Response(200, json={"messages": messages})
            )
            result = await client.poll_dispatches()
            types = {m["type"] for m in result}
            assert "dispatch" in types
            assert "resume" in types
            assert len(result) == 2


# ── Operator scoping ───────────────────────────────────────────────


class TestResumeOperatorScoping:
    """Test that resume messages from wrong operator are ignored."""

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

    async def test_resume_from_wrong_operator_is_ignored(self, daemon, config, tmp_path):
        """Resume message with different operator should be skipped."""
        repo_dir = tmp_path / "bpsai-a2a"
        repo_dir.mkdir()

        raw_msg = {
            "id": "msg-r1",
            "type": "resume",
            "operator": "other-user",
            "content": json.dumps({
                "session_id": "sess-abc",
                "target": "bpsai-a2a",
            }),
        }

        with patch("computer.dispatcher.asyncio.create_subprocess_exec") as mock_exec:
            await daemon._process_resume(raw_msg)
            mock_exec.assert_not_called()

        daemon.a2a.post_lifecycle.assert_not_called()

    async def test_resume_with_matching_operator_is_processed(self, daemon, config, tmp_path):
        """Resume message with correct operator should be processed."""
        repo_dir = tmp_path / "bpsai-a2a"
        repo_dir.mkdir()

        raw_msg = {
            "id": "msg-r1",
            "type": "resume",
            "operator": "mike",
            "content": json.dumps({
                "session_id": "sess-abc",
                "target": "bpsai-a2a",
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
            await daemon._process_resume(raw_msg)

        assert daemon.a2a.post_lifecycle.called


# ── Error handling ──────────────────────────────────────────────────


class TestResumeErrorHandling:
    """Test error cases for resume messages."""

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

    async def test_invalid_resume_message_is_logged_not_crash(self, daemon):
        """Malformed resume message should not crash the daemon."""
        raw_msg = {
            "id": "msg-r1",
            "type": "resume",
            "operator": "mike",
            "content": "not json at all",
        }
        # Should not raise
        await daemon._process_resume(raw_msg)
        daemon.a2a.post_lifecycle.assert_not_called()

    async def test_resume_missing_content_key(self, daemon):
        raw_msg = {
            "id": "msg-r1",
            "type": "resume",
            "operator": "mike",
        }
        await daemon._process_resume(raw_msg)
        daemon.a2a.post_lifecycle.assert_not_called()


# ── Poll loop routing ───────────────────────────────────────────────


class TestPollLoopRouting:
    """Test that the poll loop routes resume messages to _process_resume."""

    @pytest.fixture
    def daemon(self, config):
        from computer.daemon import Daemon
        d = Daemon(config)
        d.a2a = AsyncMock()
        d.a2a.ack_message = AsyncMock()
        d.a2a.post_result = AsyncMock()
        d.a2a.post_lifecycle = AsyncMock()
        d.a2a.post_session_output = AsyncMock()
        d.a2a.heartbeat = AsyncMock()
        return d

    async def test_poll_loop_dispatches_resume_to_process_resume(self, daemon, config, tmp_path):
        """Resume messages in the poll feed should be routed to _process_resume."""
        import asyncio

        resume_msg = {
            "id": "msg-r1",
            "type": "resume",
            "operator": "mike",
            "content": json.dumps({
                "session_id": "sess-abc",
                "target": "bpsai-a2a",
            }),
        }

        call_count = [0]

        async def mock_poll():
            call_count[0] += 1
            if call_count[0] == 1:
                return [resume_msg]
            return []

        daemon.a2a.poll_dispatches = AsyncMock(side_effect=mock_poll)
        daemon._process_resume = AsyncMock()

        async def stop_after():
            await asyncio.sleep(1.5)
            daemon.shutdown()

        asyncio.create_task(stop_after())
        await asyncio.wait_for(daemon.run(), timeout=5.0)

        daemon._process_resume.assert_called_once_with(resume_msg)
