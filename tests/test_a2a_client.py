"""Tests for the A2A HTTP client."""

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
        respx.get(f"{BASE}/messages").mock(
            return_value=httpx.Response(200, json=messages)
        )
        result = await client.poll_dispatches()
        assert len(result) == 1
        assert result[0]["id"] == "msg-1"

    @respx.mock
    async def test_poll_sends_correct_params(self, client):
        route = respx.get(f"{BASE}/messages").mock(
            return_value=httpx.Response(200, json=[])
        )
        await client.poll_dispatches()
        request = route.calls[0].request
        assert "type=dispatch" in str(request.url)
        assert "operator=mike" in str(request.url)
        assert "workspace=bpsai" in str(request.url)
        assert "unacknowledged_only=true" in str(request.url)

    @respx.mock
    async def test_poll_returns_empty_on_error(self, client):
        respx.get(f"{BASE}/messages").mock(
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


class TestHeartbeat:
    """Test sending heartbeat."""

    @respx.mock
    async def test_heartbeat(self, client):
        route = respx.post(f"{BASE}/agents/bpsai-computer/heartbeat").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        await client.heartbeat()
        assert route.called
