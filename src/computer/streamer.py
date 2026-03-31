"""Output streaming: buffer lines, scrub credentials, batch-post to A2A."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from computer.config import DaemonConfig
from computer.scrubber import scrub_credentials

log = logging.getLogger(__name__)


@dataclass
class StreamLine:
    """A single line of subprocess output."""

    line_number: int
    content: str
    stream: str  # "stdout" or "stderr"
    timestamp: str


class OutputStreamer:
    """Buffers subprocess output lines and posts them to A2A in batches."""

    def __init__(self, session_id: str, a2a: object, config: DaemonConfig) -> None:
        self._session_id = session_id
        self._a2a = a2a
        self._batch_interval = config.stream_batch_interval
        self._buffer_limit = config.stream_buffer_limit
        self._buffer: list[StreamLine] = []
        self._line_count = 0
        self._flush_task: asyncio.Task | None = None

    def add_line(self, content: str, stream: str = "stdout") -> None:
        """Add a line to the buffer. Scrubs credentials and applies backpressure."""
        scrubbed = scrub_credentials(content)
        self._line_count += 1
        line = StreamLine(
            line_number=self._line_count,
            content=scrubbed,
            stream=stream,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._buffer.append(line)
        if len(self._buffer) > self._buffer_limit:
            self._buffer = self._buffer[-self._buffer_limit:]

    def start(self) -> None:
        """Start the periodic flush loop."""
        self._flush_task = asyncio.create_task(self._flush_loop())

    async def stop(self) -> None:
        """Stop the flush loop and flush remaining lines."""
        if self._flush_task is not None:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None
        await self.flush()

    async def flush(self) -> None:
        """Post buffered lines to A2A and clear the buffer."""
        if not self._buffer:
            return
        batch = self._buffer[:]
        self._buffer.clear()
        try:
            await self._a2a.post_session_output(
                session_id=self._session_id, lines=batch
            )
        except Exception as exc:
            log.warning("Failed to post session output: %s", exc)

    async def _flush_loop(self) -> None:
        """Periodically flush buffered lines."""
        while True:
            await asyncio.sleep(self._batch_interval)
            await self.flush()
