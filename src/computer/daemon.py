"""Dispatch daemon: poll loop + graceful shutdown."""

from __future__ import annotations

import asyncio
import logging

from computer.a2a_client import A2AClient
from computer.config import DaemonConfig
from computer.dispatcher import DispatchExecutor, parse_dispatch

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
        """Process a single dispatch message: ack, execute, post result."""
        try:
            msg = parse_dispatch(raw_msg)
        except (KeyError, Exception) as exc:
            log.error("Failed to parse dispatch: %s", exc)
            return

        # Ack immediately
        await self.a2a.ack_message(msg.message_id, response="dispatched")

        # Send heartbeats while executing
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        try:
            result = await self.executor.execute(msg)
        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

        # Post result
        await self.a2a.post_result(
            dispatch_id=msg.message_id,
            content=result.output,
            success=result.success,
        )
        log.info("Dispatch %s complete: success=%s", msg.message_id, result.success)

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
