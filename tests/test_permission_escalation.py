"""Tests for permission escalation: A2A client methods + daemon routing (T2I.5)."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock

import httpx
import pytest
import respx

from computer.a2a_client import A2AClient
from computer.config import DaemonConfig
from computer.daemon import Daemon


BASE = "http://localhost:9999"


# ── A2A client: post permission-request ──────────────────────────


@pytest.fixture
def client():
    return A2AClient(base_url=BASE, operator="mike", workspace="bpsai")


class TestPostPermissionRequest:
    """A2A client can post permission-request messages."""

    @respx.mock
    async def test_posts_to_messages_endpoint(self, client):
        route = respx.post(f"{BASE}/messages").mock(
            return_value=httpx.Response(201, json={"id": "msg-pr-1"})
        )
        await client.post_permission_request(
            path="src/daemon.py", operation="write",
            reason="Need to patch config", task_id="T2I.5",
        )
        assert route.called

    @respx.mock
    async def test_payload_has_correct_type(self, client):
        route = respx.post(f"{BASE}/messages").mock(
            return_value=httpx.Response(201, json={"id": "msg-pr-1"})
        )
        await client.post_permission_request(
            path="src/daemon.py", operation="write",
            reason="Need to patch config", task_id="T2I.5",
        )
        body = json.loads(route.calls[0].request.content)
        assert body["type"] == "permission-request"

    @respx.mock
    async def test_payload_content_has_required_fields(self, client):
        route = respx.post(f"{BASE}/messages").mock(
            return_value=httpx.Response(201, json={"id": "msg-pr-1"})
        )
        await client.post_permission_request(
            path="src/daemon.py", operation="write",
            reason="Need to patch config", task_id="T2I.5",
        )
        body = json.loads(route.calls[0].request.content)
        content = json.loads(body["content"])
        assert content["path"] == "src/daemon.py"
        assert content["operation"] == "write"
        assert content["reason"] == "Need to patch config"
        assert content["task_id"] == "T2I.5"

    @respx.mock
    async def test_includes_operator_and_workspace(self, client):
        route = respx.post(f"{BASE}/messages").mock(
            return_value=httpx.Response(201, json={"id": "msg-pr-1"})
        )
        await client.post_permission_request(
            path="/p", operation="read", reason="r", task_id="T1",
        )
        body = json.loads(route.calls[0].request.content)
        assert body["operator"] == "mike"
        assert body["workspace"] == "bpsai"

    @respx.mock
    async def test_handles_error_gracefully(self, client):
        respx.post(f"{BASE}/messages").mock(
            return_value=httpx.Response(500, text="fail")
        )
        # Should not raise
        await client.post_permission_request(
            path="/p", operation="read", reason="r", task_id="T1",
        )


# ── A2A client: post permission-response ─────────────────────────


class TestPostPermissionResponse:
    """A2A client can post permission-response messages."""

    @respx.mock
    async def test_posts_to_messages_endpoint(self, client):
        route = respx.post(f"{BASE}/messages").mock(
            return_value=httpx.Response(201, json={"id": "msg-pres-1"})
        )
        await client.post_permission_response(
            approved=True, scope="file", ttl=3600,
            request_id="msg-pr-1",
        )
        assert route.called

    @respx.mock
    async def test_payload_has_correct_type(self, client):
        route = respx.post(f"{BASE}/messages").mock(
            return_value=httpx.Response(201, json={"id": "msg-pres-1"})
        )
        await client.post_permission_response(
            approved=True, scope="file", ttl=3600,
        )
        body = json.loads(route.calls[0].request.content)
        assert body["type"] == "permission-response"

    @respx.mock
    async def test_payload_content_has_required_fields(self, client):
        route = respx.post(f"{BASE}/messages").mock(
            return_value=httpx.Response(201, json={"id": "msg-pres-1"})
        )
        await client.post_permission_response(
            approved=True, scope="directory", ttl=1800,
            request_id="msg-pr-1",
        )
        body = json.loads(route.calls[0].request.content)
        content = json.loads(body["content"])
        assert content["approved"] is True
        assert content["scope"] == "directory"
        assert content["ttl"] == 1800
        assert content["request_id"] == "msg-pr-1"

    @respx.mock
    async def test_handles_error_gracefully(self, client):
        respx.post(f"{BASE}/messages").mock(
            return_value=httpx.Response(500, text="fail")
        )
        await client.post_permission_response(
            approved=False, scope="file", ttl=0,
        )


# ── A2A client: poll includes permission-response ────────────────


class TestPollIncludesPermissionResponse:
    """poll_dispatches returns permission-response messages for daemon routing."""

    @respx.mock
    async def test_permission_response_included_in_poll(self, client):
        messages = [
            {"id": "msg-1", "type": "permission-response", "content": "{}"},
        ]
        respx.get(f"{BASE}/messages/feed").mock(
            return_value=httpx.Response(200, json={"messages": messages})
        )
        result = await client.poll_dispatches()
        assert len(result) == 1
        assert result[0]["type"] == "permission-response"

    @respx.mock
    async def test_permission_request_not_polled_by_daemon(self, client):
        """Daemon shouldn't poll for permission-requests (those go to CC)."""
        messages = [
            {"id": "msg-1", "type": "permission-request", "content": "{}"},
        ]
        respx.get(f"{BASE}/messages/feed").mock(
            return_value=httpx.Response(200, json={"messages": messages})
        )
        result = await client.poll_dispatches()
        assert len(result) == 0


# ── Daemon: permission-response handler ──────────────────────────


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
    d = Daemon(config)
    d.a2a = AsyncMock()
    d.a2a.poll_dispatches = AsyncMock(return_value=[])
    d.a2a.ack_message = AsyncMock()
    d.a2a.post_result = AsyncMock()
    d.a2a.post_lifecycle = AsyncMock()
    d.a2a.post_session_output = AsyncMock()
    d.a2a.heartbeat = AsyncMock()
    return d


class TestDaemonPermissionResponseHandler:
    """Daemon registers and routes permission-response messages."""

    def test_permission_response_handler_registered(self, daemon):
        """permission-response handler is registered by default."""
        assert "permission-response" in daemon._message_handlers

    async def test_permission_response_routed_to_handler(self, daemon):
        """A permission-response message is routed to its handler."""
        # Pre-register the request_id so SEC-001 pending check passes
        daemon._pending_permission_requests.add("msg-pr-1")

        raw_msg = {
            "id": "msg-pres-1",
            "type": "permission-response",
            "operator": daemon.config.operator,
            "content": json.dumps({
                "approved": True, "scope": "file", "ttl": 3600,
                "request_id": "msg-pr-1",
            }),
        }

        call_count = [0]

        async def mock_poll():
            call_count[0] += 1
            if call_count[0] == 1:
                return [raw_msg]
            return []

        daemon.a2a.poll_dispatches = AsyncMock(side_effect=mock_poll)

        async def stop_after():
            await asyncio.sleep(0.5)
            daemon.shutdown()

        asyncio.create_task(stop_after())
        await asyncio.wait_for(daemon.run(), timeout=5.0)

        daemon.a2a.ack_message.assert_any_call(
            "msg-pres-1", response="permission-noted",
        )

    async def test_permission_response_denied_is_acked(self, daemon):
        """A denied permission-response is still acked."""
        # Pre-register the request_id so SEC-001 pending check passes
        daemon._pending_permission_requests.add("msg-pr-deny")

        raw_msg = {
            "id": "msg-pres-2",
            "type": "permission-response",
            "operator": daemon.config.operator,
            "content": json.dumps({
                "approved": False, "scope": "file", "ttl": 0,
                "request_id": "msg-pr-deny",
            }),
        }

        call_count = [0]

        async def mock_poll():
            call_count[0] += 1
            if call_count[0] == 1:
                return [raw_msg]
            return []

        daemon.a2a.poll_dispatches = AsyncMock(side_effect=mock_poll)

        async def stop_after():
            await asyncio.sleep(0.5)
            daemon.shutdown()

        asyncio.create_task(stop_after())
        await asyncio.wait_for(daemon.run(), timeout=5.0)

        daemon.a2a.ack_message.assert_any_call(
            "msg-pres-2", response="permission-noted",
        )

    async def test_malformed_permission_response_logged(self, daemon, caplog):
        """Malformed permission-response content is logged, not crash."""
        import logging

        raw_msg = {
            "id": "msg-pres-bad",
            "type": "permission-response",
            "operator": daemon.config.operator,
            "content": "not-json",
        }

        call_count = [0]

        async def mock_poll():
            call_count[0] += 1
            if call_count[0] == 1:
                return [raw_msg]
            return []

        daemon.a2a.poll_dispatches = AsyncMock(side_effect=mock_poll)

        async def stop_after():
            await asyncio.sleep(0.5)
            daemon.shutdown()

        asyncio.create_task(stop_after())
        with caplog.at_level(logging.WARNING):
            await asyncio.wait_for(daemon.run(), timeout=5.0)
        assert any("permission-response" in r.message for r in caplog.records)
