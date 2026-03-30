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

    def test_parse_missing_fields_raises(self):
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
        # Create the target repo directory
        repo_dir = tmp_path / "bpsai-a2a"
        repo_dir.mkdir()

        msg = DispatchMessage(
            message_id="msg-1",
            agent="security-auditor",
            target="bpsai-a2a",
            prompt="audit this repo",
        )

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"audit output", b""))
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

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(side_effect=TimeoutError)
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

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"partial output", b"error details"))
        mock_proc.returncode = 1

        with patch("computer.dispatcher.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await executor.execute(msg)
            assert not result.success
            assert "exit code 1" in result.output.lower()
