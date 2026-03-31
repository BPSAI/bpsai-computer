"""Dispatch daemon: poll loop + graceful shutdown."""

from __future__ import annotations

import asyncio
import logging
import platform
import time
import uuid

from computer.a2a_client import A2AClient
from computer.config import DaemonConfig
from computer.dispatcher import DispatchExecutor, parse_dispatch
from computer.lifecycle import SessionLifecycle, extract_session_id
from computer.streamer import OutputStreamer

log = logging.getLogger(__name__)


class Daemon:
    """Main daemon that polls A2A for dispatch messages and executes them."""

    def __init__(self, config: DaemonConfig) -> None:
        self.config = config
        self.running = False
        self._processed_ids: set[str] = set()
        self.a2a = A2AClient(
            base_url=config.a2a_url,
            operator=config.operator,
            workspace=config.workspace,
        )
        self.executor = DispatchExecutor(config)

    def shutdown(self) -> None:
        log.info("Shutdown requested")
        self.running = False

    async def _process_dispatch(self, raw_msg: dict) -> None:
        """Process a single dispatch message: ack, execute, post lifecycle + result."""
        try:
            msg = parse_dispatch(raw_msg)
        except (KeyError, Exception) as exc:
            log.error("Failed to parse dispatch: %s", exc)
            return

        # Ack immediately
        await self.a2a.ack_message(msg.message_id, response="dispatched")

        # Generate preliminary session ID (may be replaced by Claude Code output)
        preliminary_session_id = str(uuid.uuid4())
        lifecycle = SessionLifecycle(a2a=self.a2a)
        command = f"claude -p '{msg.prompt}' --dangerously-skip-permissions"

        # Post session-started
        await lifecycle.post_started(
            session_id=preliminary_session_id,
            operator=self.config.operator,
            machine=platform.node(),
            workspace=self.config.workspace,
            command=command,
        )

        # Set up streaming and heartbeats
        streamer = OutputStreamer(
            session_id=msg.message_id,
            a2a=self.a2a,
            config=self.config,
        )
        streamer.start()
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        start_time = time.monotonic()
        try:
            result = await self.executor.execute(msg, streamer=streamer)
        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
            await streamer.stop()
        duration = time.monotonic() - start_time

        # Extract real session ID from stdout (falls back to preliminary)
        stdout_lines = getattr(streamer, "stdout_lines", [])
        session_id = extract_session_id(stdout_lines, fallback_id=preliminary_session_id)

        # Post lifecycle complete/failed
        if result.success:
            await lifecycle.post_complete(
                session_id=session_id,
                exit_code=0,
                duration_seconds=round(duration, 1),
                output_summary=result.output,
            )
        else:
            is_timeout = "timeout" in result.output.lower()
            await lifecycle.post_failed(
                session_id=session_id,
                error=result.output,
                exit_code=None if is_timeout else self._extract_exit_code(result.output),
            )

        # Post result
        await self.a2a.post_result(
            dispatch_id=msg.message_id,
            content=result.output,
            success=result.success,
        )
        log.info("Dispatch %s complete: success=%s session=%s", msg.message_id, result.success, session_id)

    @staticmethod
    def _extract_exit_code(output: str) -> int | None:
        """Try to extract exit code from output like 'Exit code 1'."""
        import re
        m = re.search(r"[Ee]xit code (\d+)", output)
        return int(m.group(1)) if m else None

    async def _heartbeat_loop(self) -> None:
        """Send heartbeats every 30s while a dispatch is running."""
        while True:
            await asyncio.sleep(30)
            await self.a2a.heartbeat()

    async def run(self) -> None:
        """Main loop: poll, dispatch, repeat. Exits when self.running is False."""
        self.running = True
        log.info(
            "Daemon started: operator=%s workspace=%s",
            self.config.operator,
            self.config.workspace,
        )
        try:
            while self.running:
                messages = await self.a2a.poll_dispatches()
                for raw_msg in messages:
                    if not self.running:
                        break
                    msg_id = raw_msg.get("id", "")
                    if msg_id in self._processed_ids:
                        continue
                    self._processed_ids.add(msg_id)
                    await self._process_dispatch(raw_msg)
                await asyncio.sleep(self.config.poll_interval)
        except asyncio.CancelledError:
            pass
        finally:
            self.running = False
            log.info("Daemon stopped")
