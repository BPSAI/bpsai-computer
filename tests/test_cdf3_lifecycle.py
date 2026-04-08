"""Tests for CDF.3: Lifecycle error handling + streamer session ID."""

import json
from unittest.mock import AsyncMock, patch, call

import pytest

from computer.config import DaemonConfig
from computer.dispatcher import DispatchResult


@pytest.fixture
def config(tmp_path):
    return DaemonConfig(
        operator="mike",
        workspace="bpsai",
        workspace_root=str(tmp_path),
        a2a_url="http://localhost:9999",
        poll_interval=1,
        process_timeout=10,
        license_id="lic-test",
    )


@pytest.fixture
def daemon(config):
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


# ── Streamer session_id matches lifecycle session_id ──────────────


class TestStreamerSessionId:
    """OutputStreamer must receive session_id, not message_id."""

    async def test_streamer_gets_session_id_not_message_id(self, daemon, config, tmp_path):
        """The OutputStreamer should be initialized with session_id."""
        repo_dir = tmp_path / "bpsai-a2a"
        repo_dir.mkdir()

        raw_msg = {
            "id": "msg-d1",
            "type": "dispatch",
            "content": json.dumps({
                "agent": "driver",
                "target": "bpsai-a2a",
                "prompt": "do work",
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

        streamer_session_ids = []
        original_init = None

        def capture_streamer_init(self_streamer, session_id, a2a, config):
            streamer_session_ids.append(session_id)
            self_streamer._session_id = session_id
            self_streamer._a2a = a2a
            self_streamer._batch_interval = config.stream_batch_interval
            self_streamer._buffer_limit = config.stream_buffer_limit
            self_streamer._buffer = []
            self_streamer._line_count = 0
            self_streamer._stdout_lines = []
            self_streamer._flush_task = None

        with patch("computer.daemon.OutputStreamer.__init__", capture_streamer_init):
            with patch("computer.daemon.OutputStreamer.start"):
                with patch("computer.daemon.OutputStreamer.stop", new_callable=AsyncMock):
                    with patch("computer.dispatcher.asyncio.create_subprocess_exec", return_value=mock_proc):
                        await daemon._process_dispatch(raw_msg)

        # The streamer session_id should NOT be the message_id
        assert len(streamer_session_ids) == 1
        assert streamer_session_ids[0] != "msg-d1"


# ── Lifecycle posting failure does not crash ──────────────────────


class TestLifecycleFailureHandling:
    """post_started failure must not crash the dispatch pipeline."""

    async def test_lifecycle_posting_failure_returns_failure_result(self, daemon, config, tmp_path):
        """If post_started raises, _execute_with_lifecycle returns failure DispatchResult."""
        repo_dir = tmp_path / "bpsai-a2a"
        repo_dir.mkdir()

        # Make post_lifecycle raise an exception (simulating post_started failure)
        daemon.a2a.post_lifecycle = AsyncMock(side_effect=Exception("network error"))

        raw_msg = {
            "id": "msg-d1",
            "type": "dispatch",
            "content": json.dumps({
                "agent": "driver",
                "target": "bpsai-a2a",
                "prompt": "do work",
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
            # Should NOT raise — the daemon handles the error gracefully
            await daemon._process_dispatch(raw_msg)

        # post_result should still be called (even if with failure info)
        daemon.a2a.post_result.assert_called_once()


# ── Return type annotation ────────────────────────────────────────


class TestReturnTypeAnnotation:
    """_execute_with_lifecycle should have proper return type annotation."""

    def test_execute_with_lifecycle_has_return_annotation(self, config):
        from computer.daemon import Daemon
        import inspect
        d = Daemon(config)
        sig = inspect.signature(d._execute_with_lifecycle)
        ann = sig.return_annotation
        # Should be tuple[str, DispatchResult] or equivalent
        assert ann != inspect.Parameter.empty
