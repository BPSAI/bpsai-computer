"""Tests for signal push integration in the daemon poll loop."""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

from computer.config import DaemonConfig
from computer.daemon import Daemon

BASE = "http://localhost:9999"


def _make_signal(ts="2026-03-31T00:00:00+00:00"):
    return json.dumps({
        "signal_type": "api_failure",
        "severity": "warning",
        "timestamp": ts,
        "session_id": "",
        "payload": {"stop_reason": "subagent_stop"},
        "source": "automated",
    })


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


@pytest.fixture
def config(workspace, tmp_path):
    return DaemonConfig(
        operator="mike",
        workspace="bpsai",
        workspace_root=str(workspace),
        a2a_url=BASE,
        poll_interval=1,
        process_timeout=30,
        license_id="lic-test",
    )


class TestDaemonSignalPush:
    """AC: Push runs on each poll cycle (same cadence as dispatch polling)."""

    async def test_daemon_creates_signal_pusher(self, config):
        daemon = Daemon(config)
        assert daemon.signal_pusher is not None

    @respx.mock
    async def test_signal_push_runs_each_poll_cycle(self, config, workspace):
        """Signal push is called on each iteration of the poll loop."""
        # Create a repo with signals
        repo = workspace / "my-repo"
        signals_dir = repo / ".paircoder" / "telemetry"
        signals_dir.mkdir(parents=True)
        (signals_dir / "signals.jsonl").write_text(_make_signal() + "\n")

        daemon = Daemon(config)

        # Mock poll to return empty (no dispatches)
        respx.get(f"{BASE}/messages/feed").mock(
            return_value=httpx.Response(200, json={"messages": []})
        )
        # Mock signal push endpoint
        signal_route = respx.post(f"{BASE}/signals").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        async def stop_after_one_cycle():
            await asyncio.sleep(0.3)
            daemon.shutdown()

        asyncio.create_task(stop_after_one_cycle())
        await asyncio.wait_for(daemon.run(), timeout=5.0)

        assert signal_route.called

    @respx.mock
    async def test_signal_push_failure_does_not_block_polling(self, config, workspace):
        """If signal push fails, dispatch polling continues."""
        repo = workspace / "my-repo"
        signals_dir = repo / ".paircoder" / "telemetry"
        signals_dir.mkdir(parents=True)
        (signals_dir / "signals.jsonl").write_text(_make_signal() + "\n")

        daemon = Daemon(config)

        poll_count = 0

        def poll_side_effect(request):
            nonlocal poll_count
            poll_count += 1
            return httpx.Response(200, json={"messages": []})

        respx.get(f"{BASE}/messages/feed").mock(side_effect=poll_side_effect)
        respx.post(f"{BASE}/signals").mock(
            return_value=httpx.Response(500, text="error")
        )

        async def stop_after_two_cycles():
            await asyncio.sleep(2.5)
            daemon.shutdown()

        asyncio.create_task(stop_after_two_cycles())
        await asyncio.wait_for(daemon.run(), timeout=10.0)

        # Polling continued despite signal push failure
        assert poll_count >= 2

    async def test_signal_pusher_closed_on_shutdown(self, config):
        daemon = Daemon(config)
        daemon.signal_pusher.close = AsyncMock()

        daemon.running = True

        async def stop_soon():
            await asyncio.sleep(0.1)
            daemon.shutdown()

        asyncio.create_task(stop_soon())
        await asyncio.wait_for(daemon.run(), timeout=5.0)

        daemon.signal_pusher.close.assert_called_once()
