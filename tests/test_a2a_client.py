"""Tests for the A2A HTTP client."""

import time
from unittest.mock import AsyncMock

import httpx
import pytest
import respx

from computer.a2a_client import A2AClient


BASE = "http://localhost:9999"


@pytest.fixture
def client():
    return A2AClient(base_url=BASE, operator="mike", workspace="bpsai")


class TestPollDispatches:
    """Test polling for dispatch messages."""

    @respx.mock
    async def test_poll_returns_messages(self, client):
        messages = [
            {
                "id": "msg-1",
                "type": "dispatch",
                "operator": "mike",
                "workspace": "bpsai",
                "content": '{"agent": "security-auditor", "target": "bpsai-a2a", "prompt": "audit this repo"}',
                "sender": "command-center",
                "created_at": "2026-03-30T00:00:00Z",
            }
        ]
        respx.get(f"{BASE}/messages/feed").mock(
            return_value=httpx.Response(200, json={"messages": messages})
        )
        result = await client.poll_dispatches()
        assert len(result) == 1
        assert result[0]["id"] == "msg-1"

    @respx.mock
    async def test_poll_sends_correct_params(self, client):
        route = respx.get(f"{BASE}/messages/feed").mock(
            return_value=httpx.Response(200, json={"messages": []})
        )
        await client.poll_dispatches()
        request = route.calls[0].request
        assert "agent=computer" in str(request.url)
        assert "operator=mike" in str(request.url)
        assert "workspace=bpsai" in str(request.url)
        assert "limit=10" in str(request.url)

    @respx.mock
    async def test_poll_returns_empty_on_error(self, client):
        respx.get(f"{BASE}/messages/feed").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        result = await client.poll_dispatches()
        assert result == []


class TestAckMessage:
    """Test acknowledging dispatch messages."""

    @respx.mock
    async def test_ack_posts_correctly(self, client):
        route = respx.post(f"{BASE}/messages/ack").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        await client.ack_message("msg-1", response="dispatched")
        body = route.calls[0].request.content
        assert b"msg-1" in body
        assert b"dispatched" in body

    @respx.mock
    async def test_ack_handles_error(self, client):
        respx.post(f"{BASE}/messages/ack").mock(
            return_value=httpx.Response(500, text="fail")
        )
        # Should not raise
        await client.ack_message("msg-1", response="dispatched")


class TestPostResult:
    """Test posting dispatch results."""

    @respx.mock
    async def test_post_result(self, client):
        route = respx.post(f"{BASE}/messages").mock(
            return_value=httpx.Response(201, json={"id": "msg-2"})
        )
        await client.post_result(
            dispatch_id="msg-1",
            content="Audit complete. No issues found.",
            success=True,
        )
        body = route.calls[0].request.content
        assert b"dispatch-result" in body
        assert b"mike" in body
        assert b"bpsai" in body

    @respx.mock
    async def test_post_result_failure(self, client):
        route = respx.post(f"{BASE}/messages").mock(
            return_value=httpx.Response(201, json={"id": "msg-3"})
        )
        await client.post_result(
            dispatch_id="msg-1",
            content="Process timed out",
            success=False,
        )
        body = route.calls[0].request.content
        assert b"dispatch-result" in body


class TestPostSessionOutput:
    """Test posting session output (streaming lines)."""

    @respx.mock
    async def test_post_session_output(self, client):
        route = respx.post(f"{BASE}/messages").mock(
            return_value=httpx.Response(201, json={"id": "msg-out-1"})
        )
        from computer.streamer import StreamLine

        lines = [
            StreamLine(line_number=1, content="hello", stream="stdout", timestamp="2026-03-30T00:00:00"),
            StreamLine(line_number=2, content="world", stream="stderr", timestamp="2026-03-30T00:00:01"),
        ]
        await client.post_session_output(session_id="sess-1", lines=lines)
        assert route.called
        body = route.calls[0].request.content
        assert b"session-output" in body
        assert b"sess-1" in body

    @respx.mock
    async def test_post_session_output_handles_error(self, client):
        respx.post(f"{BASE}/messages").mock(
            return_value=httpx.Response(500, text="fail")
        )
        from computer.streamer import StreamLine

        lines = [StreamLine(1, "x", "stdout", "2026-03-30T00:00:00")]
        # Should not raise
        await client.post_session_output(session_id="sess-1", lines=lines)


class TestHeartbeat:
    """Test sending heartbeat."""

    @respx.mock
    async def test_heartbeat(self, client):
        route = respx.post(f"{BASE}/agents/bpsai-computer/heartbeat").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        await client.heartbeat()
        assert route.called


class TestBearerAuth:
    """Test that Authorization: Bearer header is included when TokenManager is provided."""

    @pytest.fixture
    def token_manager(self):
        mgr = AsyncMock()
        mgr.get_token = AsyncMock(return_value="jwt-test-token")
        return mgr

    @pytest.fixture
    def auth_client(self, token_manager):
        return A2AClient(
            base_url=BASE, operator="mike", workspace="bpsai",
            token_manager=token_manager,
        )

    @respx.mock
    async def test_poll_includes_bearer(self, auth_client):
        route = respx.get(f"{BASE}/messages/feed").mock(
            return_value=httpx.Response(200, json={"messages": []})
        )
        await auth_client.poll_dispatches()
        auth_header = route.calls[0].request.headers.get("authorization")
        assert auth_header == "Bearer jwt-test-token"

    @respx.mock
    async def test_ack_includes_bearer(self, auth_client):
        route = respx.post(f"{BASE}/messages/ack").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        await auth_client.ack_message("msg-1")
        auth_header = route.calls[0].request.headers.get("authorization")
        assert auth_header == "Bearer jwt-test-token"

    @respx.mock
    async def test_post_result_includes_bearer(self, auth_client):
        route = respx.post(f"{BASE}/messages").mock(
            return_value=httpx.Response(201, json={"id": "msg-2"})
        )
        await auth_client.post_result(dispatch_id="msg-1", content="ok", success=True)
        auth_header = route.calls[0].request.headers.get("authorization")
        assert auth_header == "Bearer jwt-test-token"

    @respx.mock
    async def test_heartbeat_includes_bearer(self, auth_client):
        route = respx.post(f"{BASE}/agents/bpsai-computer/heartbeat").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        await auth_client.heartbeat()
        auth_header = route.calls[0].request.headers.get("authorization")
        assert auth_header == "Bearer jwt-test-token"

    @respx.mock
    async def test_no_bearer_without_token_manager(self, client):
        """Client without token_manager should not send Authorization header."""
        route = respx.get(f"{BASE}/messages/feed").mock(
            return_value=httpx.Response(200, json={"messages": []})
        )
        await client.poll_dispatches()
        auth_header = route.calls[0].request.headers.get("authorization")
        assert auth_header is None

    @respx.mock
    async def test_no_bearer_when_token_is_none(self):
        """When token_manager returns None, no Authorization header sent."""
        mgr = AsyncMock()
        mgr.get_token = AsyncMock(return_value=None)
        client = A2AClient(
            base_url=BASE, operator="mike", workspace="bpsai",
            token_manager=mgr,
        )
        route = respx.get(f"{BASE}/messages/feed").mock(
            return_value=httpx.Response(200, json={"messages": []})
        )
        await client.poll_dispatches()
        auth_header = route.calls[0].request.headers.get("authorization")
        assert auth_header is None
