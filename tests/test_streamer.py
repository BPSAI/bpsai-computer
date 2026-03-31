"""Tests for output streaming: line-by-line reading, batched posting, backpressure."""

from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from computer.config import DaemonConfig
from computer.streamer import OutputStreamer, StreamLine


@pytest.fixture
def config(tmp_path):
    return DaemonConfig(
        operator="mike",
        workspace="bpsai",
        workspace_root=str(tmp_path),
        a2a_url="http://localhost:9999",
        poll_interval=1,
        process_timeout=10,
        stream_batch_interval=0.1,
        stream_buffer_limit=5,
    )


@pytest.fixture
def mock_a2a():
    a2a = AsyncMock()
    a2a.post_session_output = AsyncMock()
    return a2a


@pytest.fixture
def streamer(config, mock_a2a):
    return OutputStreamer(session_id="sess-1", a2a=mock_a2a, config=config)


class TestStreamLine:
    """StreamLine dataclass structure."""

    def test_stream_line_fields(self):
        line = StreamLine(
            line_number=1,
            content="hello",
            stream="stdout",
            timestamp="2026-03-30T00:00:00",
        )
        assert line.line_number == 1
        assert line.content == "hello"
        assert line.stream == "stdout"


class TestOutputStreamerAddLine:
    """Test adding lines to the streamer buffer."""

    def test_add_line_increments_line_number(self, streamer):
        streamer.add_line("line one", stream="stdout")
        streamer.add_line("line two", stream="stdout")
        assert len(streamer._buffer) == 2
        assert streamer._buffer[0].line_number == 1
        assert streamer._buffer[1].line_number == 2

    def test_add_line_scrubs_credentials(self, streamer):
        streamer.add_line("key=sk-ant-abcdefghijklmnop", stream="stdout")
        assert "sk-ant" not in streamer._buffer[0].content
        assert "REDACTED" in streamer._buffer[0].content

    def test_add_line_records_stream_type(self, streamer):
        streamer.add_line("out line", stream="stdout")
        streamer.add_line("err line", stream="stderr")
        assert streamer._buffer[0].stream == "stdout"
        assert streamer._buffer[1].stream == "stderr"

    def test_add_line_sets_timestamp(self, streamer):
        streamer.add_line("hello", stream="stdout")
        dt = datetime.fromisoformat(streamer._buffer[0].timestamp)
        assert dt.year >= 2026


class TestOutputStreamerBackpressure:
    """Test buffer overflow / backpressure handling."""

    def test_buffer_drops_oldest_when_limit_exceeded(self, streamer):
        for i in range(8):
            streamer.add_line(f"line {i}", stream="stdout")
        assert len(streamer._buffer) == 5
        assert streamer._buffer[0].content == "line 3"
        assert streamer._buffer[-1].content == "line 7"


class TestOutputStreamerFlush:
    """Test batched flushing to A2A."""

    async def test_flush_posts_buffered_lines(self, streamer, mock_a2a):
        streamer.add_line("line one", stream="stdout")
        streamer.add_line("line two", stream="stderr")
        await streamer.flush()
        mock_a2a.post_session_output.assert_called_once()
        call_args = mock_a2a.post_session_output.call_args
        assert call_args[1]["session_id"] == "sess-1"
        lines = call_args[1]["lines"]
        assert len(lines) == 2

    async def test_flush_clears_buffer(self, streamer, mock_a2a):
        streamer.add_line("line one", stream="stdout")
        await streamer.flush()
        assert len(streamer._buffer) == 0

    async def test_flush_skips_when_buffer_empty(self, streamer, mock_a2a):
        await streamer.flush()
        mock_a2a.post_session_output.assert_not_called()

    async def test_periodic_flush_fires(self, streamer, mock_a2a):
        """Start streamer, add lines, wait for auto-flush."""
        streamer.start()
        streamer.add_line("auto-flush me", stream="stdout")
        await asyncio.sleep(0.25)
        await streamer.stop()
        mock_a2a.post_session_output.assert_called()

    async def test_stop_flushes_remaining(self, streamer, mock_a2a):
        """Stop should flush any remaining buffered lines."""
        streamer.add_line("leftover", stream="stdout")
        await streamer.stop()
        mock_a2a.post_session_output.assert_called_once()
        lines = mock_a2a.post_session_output.call_args[1]["lines"]
        assert lines[0].content == "leftover"
