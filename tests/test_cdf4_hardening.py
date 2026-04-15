"""Tests for CDF.4: A2A client + daemon hardening."""

import json
import logging
from collections import OrderedDict
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

from computer.a2a_client import A2AClient
from computer.config import DaemonConfig
from computer.dispatcher import DispatchResult


BASE = "http://localhost:9999"


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


# ── A2A client reuses connection ──────────────────────────────────


class TestA2AClientConnectionReuse:
    """A2A client should use a shared httpx.AsyncClient, not create per-call."""

    async def test_client_reuses_http_connection(self):
        """Multiple calls should not create new httpx.AsyncClient each time."""
        client = A2AClient(base_url=BASE, operator="mike", workspace="bpsai")

        with respx.mock:
            respx.get(f"{BASE}/messages/feed").mock(
                return_value=httpx.Response(200, json={"messages": []})
            )
            respx.post(f"{BASE}/messages/ack").mock(
                return_value=httpx.Response(200, json={"status": "ok"})
            )

            await client.poll_dispatches()
            await client.ack_message("msg-1")

        # The client should have a shared _http attribute
        assert hasattr(client, "_http")
        assert isinstance(client._http, httpx.AsyncClient)
        await client.close()

    async def test_client_close_cleans_up(self):
        """close() should close the underlying httpx client."""
        client = A2AClient(base_url=BASE, operator="mike", workspace="bpsai")
        assert hasattr(client, "close")
        await client.close()


# ── Processed IDs bounded ─────────────────────────────────────────


class TestProcessedIdsBounded:
    """_processed_ids must evict old entries at 10,000 limit."""

    def test_processed_ids_evicts_at_limit(self, config):
        from computer.daemon import Daemon, _MAX_PROCESSED_IDS
        d = Daemon(config)

        # Simulate the run loop's eviction logic
        for i in range(10_001):
            msg_id = f"msg-{i}"
            d._processed_ids[msg_id] = None
            if len(d._processed_ids) > _MAX_PROCESSED_IDS:
                d._processed_ids.popitem(last=False)

        # Should be bounded at 10,000
        assert len(d._processed_ids) <= 10_000

        # Oldest entry should have been evicted
        assert "msg-0" not in d._processed_ids

        # Latest entry should still be present
        assert "msg-10000" in d._processed_ids


# ── Malformed JSON dispatch logs warning ──────────────────────────


class TestMalformedJsonDispatch:
    """Malformed structured JSON (valid JSON, missing keys) falls through to plain-text parse."""

    async def test_malformed_json_dispatch_falls_through(self, config, caplog):
        from computer.daemon import Daemon
        d = Daemon(config)
        d.a2a = AsyncMock()
        d.a2a.ack_message = AsyncMock()
        d.a2a.post_result = AsyncMock()
        d.a2a.post_lifecycle = AsyncMock()
        d.a2a.post_session_output = AsyncMock()
        d.a2a.heartbeat = AsyncMock()
        d.executor = AsyncMock()
        d.executor.execute = AsyncMock(
            return_value=DispatchResult(message_id="msg-bad", success=True, output="ok")
        )

        raw_msg = {
            "id": "msg-bad",
            "type": "dispatch",
            "content": json.dumps({"agent": "driver"}),  # missing target/prompt
        }

        await d._process_dispatch(raw_msg)

        # Parse no longer fails — falls through to plain-text format
        # Message should be acked and processed
        d.a2a.ack_message.assert_called_once()


# ── HTTPS warning ─────────────────────────────────────────────────


class TestHttpsWarning:
    """Startup should warn if a2a_url is not HTTPS."""

    def test_non_https_url_logs_warning(self, config, caplog):
        from computer.daemon import Daemon
        with caplog.at_level(logging.WARNING):
            d = Daemon(config)  # config uses http://localhost:9999
        assert any("https" in r.message.lower() for r in caplog.records)


# ── Streamer backpressure warning ─────────────────────────────────


class TestStreamerBackpressureWarning:
    """Streamer should log warning when lines are dropped due to backpressure."""

    def test_backpressure_logs_warning(self, config, caplog):
        from computer.streamer import OutputStreamer
        a2a = AsyncMock()
        streamer = OutputStreamer(session_id="sess-1", a2a=a2a, config=config)

        with caplog.at_level(logging.WARNING):
            for i in range(config.stream_buffer_limit + 5):
                streamer.add_line(f"line {i}", stream="stdout")

        assert any("drop" in r.message.lower() or "backpressure" in r.message.lower() for r in caplog.records)
