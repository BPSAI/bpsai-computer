"""Dispatch daemon: poll loop + graceful shutdown."""

from __future__ import annotations

import asyncio
import logging

from computer.config import DaemonConfig

log = logging.getLogger(__name__)


class Daemon:
    """Main daemon that polls A2A for dispatch messages and executes them."""

    def __init__(self, config: DaemonConfig) -> None:
        self.config = config
        self.running = False

    def shutdown(self) -> None:
        log.info("Shutdown requested")
        self.running = False

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
                await asyncio.sleep(self.config.poll_interval)
        except asyncio.CancelledError:
            pass
        finally:
            self.running = False
            log.info("Daemon stopped")
