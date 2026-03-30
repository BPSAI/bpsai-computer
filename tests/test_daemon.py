"""Tests for the daemon lifecycle (start/stop/shutdown)."""

import asyncio
import signal

import pytest

from computer.config import DaemonConfig
from computer.daemon import Daemon


@pytest.fixture
def config(tmp_path):
    return DaemonConfig(
        operator="mike",
        workspace="bpsai",
        workspace_root=str(tmp_path),
        a2a_url="http://localhost:9999",
        poll_interval=1,
        process_timeout=30,
    )


class TestDaemon:
    """Test daemon lifecycle."""

    async def test_daemon_creates_with_config(self, config):
        daemon = Daemon(config)
        assert daemon.config.operator == "mike"
        assert daemon.running is False

    async def test_daemon_stops_on_shutdown(self, config):
        daemon = Daemon(config)
        daemon.running = True
        daemon.shutdown()
        assert daemon.running is False

    async def test_daemon_run_exits_on_shutdown(self, config):
        """Daemon run loop exits promptly when shutdown is called."""
        daemon = Daemon(config)

        async def stop_after_brief():
            await asyncio.sleep(0.1)
            daemon.shutdown()

        asyncio.create_task(stop_after_brief())
        # run() should exit cleanly without hanging
        await asyncio.wait_for(daemon.run(), timeout=5.0)
        assert daemon.running is False
