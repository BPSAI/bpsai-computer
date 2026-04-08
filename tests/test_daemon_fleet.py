"""Tests for git + CI summary push integration in the daemon poll loop."""

import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest
import respx

from computer.config import DaemonConfig
from computer.daemon import Daemon

BASE = "http://localhost:9999"


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


@pytest.fixture
def config(workspace):
    return DaemonConfig(
        operator="mike",
        workspace="bpsai",
        workspace_root=str(workspace),
        a2a_url=BASE,
        poll_interval=1,
        process_timeout=30,
    )


class TestDaemonGitCIPush:
    """AC: Git + CI summaries pushed each daemon cycle alongside signal push."""

    async def test_daemon_creates_collectors(self, config):
        daemon = Daemon(config)
        assert daemon.git_collector is not None
        assert daemon.ci_collector is not None

    @respx.mock
    async def test_git_push_runs_each_cycle(self, config, workspace):
        """Git summary push called on each poll iteration."""
        # Create a git repo in workspace
        (workspace / "my-repo" / ".git").mkdir(parents=True)

        daemon = Daemon(config)
        daemon.git_collector.push_summaries = AsyncMock()
        daemon.ci_collector.push_summaries = AsyncMock()

        respx.get(f"{BASE}/messages/feed").mock(
            return_value=httpx.Response(200, json={"messages": []})
        )
        respx.post(f"{BASE}/signals").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        async def stop_after_one_cycle():
            await asyncio.sleep(0.3)
            daemon.shutdown()

        asyncio.create_task(stop_after_one_cycle())
        await asyncio.wait_for(daemon.run(), timeout=5.0)

        daemon.git_collector.push_summaries.assert_called()
        daemon.ci_collector.push_summaries.assert_called()

    @respx.mock
    async def test_git_push_failure_does_not_block_polling(self, config, workspace):
        """If git/CI push fails, dispatch polling continues."""
        daemon = Daemon(config)
        daemon.git_collector.push_summaries = AsyncMock(side_effect=Exception("git boom"))
        daemon.ci_collector.push_summaries = AsyncMock(side_effect=Exception("ci boom"))

        poll_count = 0

        def poll_side_effect(request):
            nonlocal poll_count
            poll_count += 1
            return httpx.Response(200, json={"messages": []})

        respx.get(f"{BASE}/messages/feed").mock(side_effect=poll_side_effect)
        respx.post(f"{BASE}/signals").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        async def stop_after_two_cycles():
            await asyncio.sleep(2.5)
            daemon.shutdown()

        asyncio.create_task(stop_after_two_cycles())
        await asyncio.wait_for(daemon.run(), timeout=10.0)

        assert poll_count >= 2

    async def test_collectors_closed_on_shutdown(self, config):
        daemon = Daemon(config)
        daemon.git_collector.close = AsyncMock()
        daemon.ci_collector.close = AsyncMock()

        daemon.running = True

        async def stop_soon():
            await asyncio.sleep(0.1)
            daemon.shutdown()

        asyncio.create_task(stop_soon())
        await asyncio.wait_for(daemon.run(), timeout=5.0)

        daemon.git_collector.close.assert_called_once()
        daemon.ci_collector.close.assert_called_once()
