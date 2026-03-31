"""Tests for dispatch execution (subprocess launching)."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from computer.config import DaemonConfig
from computer.dispatcher import DispatchExecutor, DispatchMessage, parse_dispatch


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


class TestParseDispatch:
    """Test parsing dispatch message content."""

    def test_parse_valid_message(self):
        raw = {
            "id": "msg-1",
            "type": "dispatch",
            "content": json.dumps({
                "agent": "security-auditor",
                "target": "bpsai-a2a",
                "prompt": "audit this repo",
            }),
        }
        msg = parse_dispatch(raw)
        assert msg.message_id == "msg-1"
        assert msg.agent == "security-auditor"
        assert msg.target == "bpsai-a2a"
        assert msg.prompt == "audit this repo"

    def test_parse_missing_structured_fields_raises(self):
        raw = {
            "id": "msg-1",
            "type": "dispatch",
            "content": json.dumps({"agent": "auditor"}),
        }
        with pytest.raises(KeyError):
            parse_dispatch(raw)


class TestDispatchExecutor:
    """Test dispatch execution logic."""

    async def test_missing_repo_returns_error(self, executor, config):
        msg = DispatchMessage(
            message_id="msg-1",
            agent="security-auditor",
            target="nonexistent-repo",
            prompt="audit",
        )
        result = await executor.execute(msg)
        assert not result.success
        assert "not found" in result.output.lower()

    async def test_execute_calls_subprocess(self, executor, config, tmp_path):
        repo_dir = tmp_path / "bpsai-a2a"
        repo_dir.mkdir()

        msg = DispatchMessage(
            message_id="msg-1",
            agent="security-auditor",
            target="bpsai-a2a",
            prompt="audit this repo",
        )

        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(side_effect=[b"audit output\n", b""])
        mock_stderr = AsyncMock()
        mock_stderr.readline = AsyncMock(side_effect=[b""])

        mock_proc = AsyncMock()
        mock_proc.stdout = mock_stdout
        mock_proc.stderr = mock_stderr
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = 0

        with patch("computer.dispatcher.asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            result = await executor.execute(msg)
            mock_exec.assert_called_once()
            call_args = mock_exec.call_args[0]
            assert "claude" in call_args[0]
            assert "-p" in call_args
            assert result.success
            assert "audit output" in result.output

    async def test_execute_handles_timeout(self, executor, config, tmp_path):
        repo_dir = tmp_path / "bpsai-a2a"
        repo_dir.mkdir()

        msg = DispatchMessage(
            message_id="msg-1",
            agent="security-auditor",
            target="bpsai-a2a",
            prompt="audit",
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
            result = await executor.execute(msg)
            assert not result.success
            assert "timeout" in result.output.lower()

    async def test_execute_handles_nonzero_exit(self, executor, config, tmp_path):
        repo_dir = tmp_path / "bpsai-a2a"
        repo_dir.mkdir()

        msg = DispatchMessage(
            message_id="msg-1",
            agent="security-auditor",
            target="bpsai-a2a",
            prompt="audit",
        )

        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(side_effect=[b"partial output\n", b""])
        mock_stderr = AsyncMock()
        mock_stderr.readline = AsyncMock(side_effect=[b"error details\n", b""])

        mock_proc = AsyncMock()
        mock_proc.stdout = mock_stdout
        mock_proc.stderr = mock_stderr
        mock_proc.wait = AsyncMock(return_value=1)
        mock_proc.returncode = 1

        with patch("computer.dispatcher.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await executor.execute(msg)
            assert not result.success
            assert "exit code 1" in result.output.lower()


class TestStreamingExecution:
    """Test line-by-line stdout/stderr reading with streamer."""

    async def test_execute_streams_stdout_lines(self, executor, config, tmp_path):
        """Executor reads stdout line-by-line and feeds to streamer."""
        repo_dir = tmp_path / "bpsai-a2a"
        repo_dir.mkdir()

        msg = DispatchMessage(
            message_id="msg-1",
            agent="driver",
            target="bpsai-a2a",
            prompt="do work",
        )

        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(side_effect=[
            b"line one\n",
            b"line two\n",
            b"",  # EOF
        ])
        mock_stderr = AsyncMock()
        mock_stderr.readline = AsyncMock(side_effect=[b""])  # no stderr

        mock_proc = AsyncMock()
        mock_proc.stdout = mock_stdout
        mock_proc.stderr = mock_stderr
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = 0

        streamer = AsyncMock()
        streamer.add_line = lambda content, stream: None
        streamer.start = AsyncMock()
        streamer.stop = AsyncMock()
        streamer.flush = AsyncMock()

        # Track add_line calls
        add_line_calls = []
        streamer.add_line = lambda content, stream: add_line_calls.append((content, stream))

        with patch("computer.dispatcher.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await executor.execute(msg, streamer=streamer)
            assert result.success
            assert len(add_line_calls) == 2
            assert add_line_calls[0] == ("line one", "stdout")
            assert add_line_calls[1] == ("line two", "stdout")

    async def test_execute_streams_stderr_lines(self, executor, config, tmp_path):
        """Executor reads stderr line-by-line and feeds to streamer."""
        repo_dir = tmp_path / "bpsai-a2a"
        repo_dir.mkdir()

        msg = DispatchMessage(
            message_id="msg-1",
            agent="driver",
            target="bpsai-a2a",
            prompt="do work",
        )

        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(side_effect=[b""])
        mock_stderr = AsyncMock()
        mock_stderr.readline = AsyncMock(side_effect=[
            b"warning: something\n",
            b"",
        ])

        mock_proc = AsyncMock()
        mock_proc.stdout = mock_stdout
        mock_proc.stderr = mock_stderr
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = 0

        add_line_calls = []
        streamer = AsyncMock()
        streamer.add_line = lambda content, stream: add_line_calls.append((content, stream))

        with patch("computer.dispatcher.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await executor.execute(msg, streamer=streamer)
            assert len(add_line_calls) == 1
            assert add_line_calls[0] == ("warning: something", "stderr")

    async def test_execute_scrubs_credentials_in_stream(self, executor, config, tmp_path):
        """Credential scrubbing happens via the streamer's add_line."""
        repo_dir = tmp_path / "bpsai-a2a"
        repo_dir.mkdir()

        msg = DispatchMessage(
            message_id="msg-1",
            agent="driver",
            target="bpsai-a2a",
            prompt="do work",
        )

        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(side_effect=[
            b"my key is sk-ant-abcdefghijklmnop\n",
            b"",
        ])
        mock_stderr = AsyncMock()
        mock_stderr.readline = AsyncMock(side_effect=[b""])

        mock_proc = AsyncMock()
        mock_proc.stdout = mock_stdout
        mock_proc.stderr = mock_stderr
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = 0

        # Without a streamer, the final result should still be scrubbed
        with patch("computer.dispatcher.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await executor.execute(msg)
            assert "sk-ant" not in result.output
            assert "REDACTED" in result.output

    async def test_execute_without_streamer_still_works(self, executor, config, tmp_path):
        """Backwards compatible: no streamer means collect all output."""
        repo_dir = tmp_path / "bpsai-a2a"
        repo_dir.mkdir()

        msg = DispatchMessage(
            message_id="msg-1",
            agent="driver",
            target="bpsai-a2a",
            prompt="do work",
        )

        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(side_effect=[
            b"line one\n",
            b"line two\n",
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
            result = await executor.execute(msg)
            assert result.success
            assert "line one" in result.output
            assert "line two" in result.output
