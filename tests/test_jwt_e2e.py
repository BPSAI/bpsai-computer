"""End-to-end JWT auth verification (CD3.5).

Verifies the full dispatch loop with JWT authentication:
  JWT auth → poll A2A → receive dispatch → execute → post result.

All A2A requests must include a valid Authorization: Bearer <token> header.
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

from computer.config import DaemonConfig
from computer.daemon import Daemon


A2A_URL = "http://localhost:9999"
API_URL = "http://localhost:8080"
TOKEN_ENDPOINT = f"{API_URL}/api/v1/auth/operator-token"
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test-jwt-token"


def _token_response():
    return httpx.Response(200, json={
        "token": JWT_TOKEN, "expires_at": time.time() + 3600,
        "tier": "pro", "operator": "mike",
    })


def _dispatch_message():
    return {
        "id": "msg-jwt-1", "type": "dispatch",
        "operator": "mike", "workspace": "bpsai",
        "content": json.dumps({
            "agent": "security-auditor", "target": "bpsai-a2a",
            "prompt": "audit this repo",
        }),
        "sender": "command-center", "created_at": "2026-04-07T00:00:00Z",
    }


def _mock_subprocess():
    """Create a mock Claude Code subprocess."""
    mock_stdout = AsyncMock()
    mock_stdout.readline = AsyncMock(side_effect=[
        b"Session: sess-jwt-001\n", b"Audit complete. 0 issues.\n", b"",
    ])
    mock_stderr = AsyncMock()
    mock_stderr.readline = AsyncMock(side_effect=[b""])
    mock_proc = AsyncMock()
    mock_proc.stdout = mock_stdout
    mock_proc.stderr = mock_stderr
    mock_proc.wait = AsyncMock(return_value=0)
    mock_proc.returncode = 0
    return mock_proc


def _assert_bearer(request: httpx.Request) -> None:
    """Assert valid Bearer Authorization header."""
    auth = request.headers.get("authorization", "")
    assert auth == f"Bearer {JWT_TOKEN}", (
        f"Missing/wrong auth on {request.method} {request.url}: '{auth}'"
    )


def _mock_a2a_with_dispatch():
    """Mock all A2A endpoints, returning one dispatch then empty polls."""
    respx.post(TOKEN_ENDPOINT).mock(return_value=_token_response())
    poll_calls = [0]

    def poll_side_effect(request):
        poll_calls[0] += 1
        if poll_calls[0] == 1:
            return httpx.Response(200, json={"messages": [_dispatch_message()]})
        return httpx.Response(200, json={"messages": []})

    routes = {
        "poll": respx.get(f"{A2A_URL}/messages/feed").mock(side_effect=poll_side_effect),
        "ack": respx.post(f"{A2A_URL}/messages/ack").mock(
            return_value=httpx.Response(200, json={"status": "ok"})),
        "messages": respx.post(f"{A2A_URL}/messages").mock(
            return_value=httpx.Response(201, json={"id": "result-1"})),
        "heartbeat": respx.post(f"{A2A_URL}/agents/bpsai-computer/heartbeat").mock(
            return_value=httpx.Response(200, json={"status": "ok"})),
    }
    return routes


async def _run_daemon_with_dispatch(config, timeout=2.5):
    """Run daemon with mocked subprocess, stop after timeout."""
    daemon = Daemon(config)
    with patch("computer.dispatcher.asyncio.create_subprocess_exec",
               return_value=_mock_subprocess()):
        async def stop_after():
            await asyncio.sleep(timeout)
            daemon.shutdown()
        asyncio.create_task(stop_after())
        await asyncio.wait_for(daemon.run(), timeout=10.0)
    return daemon


@pytest.fixture
def workspace(tmp_path):
    repo = tmp_path / "bpsai-a2a"
    repo.mkdir()
    return tmp_path


@pytest.fixture
def config_with_license(workspace):
    return DaemonConfig(
        operator="mike", workspace="bpsai",
        workspace_root=str(workspace), a2a_url=A2A_URL,
        paircoder_api_url=API_URL, license_id="lic-e2e-test",
        poll_interval=1, process_timeout=10,
    )


class TestJWTAuthEndToEnd:
    """Verify JWT is present and valid on ALL A2A requests during dispatch."""

    @respx.mock
    async def test_all_a2a_requests_include_jwt(self, config_with_license):
        """Full flow: token fetch → poll → ack → lifecycle → result — all with JWT."""
        routes = _mock_a2a_with_dispatch()
        await _run_daemon_with_dispatch(config_with_license)

        # Token was fetched
        token_calls = [c for c in respx.calls if TOKEN_ENDPOINT in str(c.request.url)]
        assert len(token_calls) >= 1

        # All poll requests have Bearer header
        for call in routes["poll"].calls:
            _assert_bearer(call.request)

        # Ack has Bearer header
        assert routes["ack"].called
        _assert_bearer(routes["ack"].calls[0].request)

        # All message posts (lifecycle + result) have Bearer header
        for call in routes["messages"].calls:
            _assert_bearer(call.request)

    @respx.mock
    async def test_daemon_starts_with_auto_discovered_license(self, workspace):
        """Daemon starts with operator from config + auto-discovered license_id."""
        config = DaemonConfig(
            operator="mike", workspace="bpsai",
            workspace_root=str(workspace), a2a_url=A2A_URL,
            paircoder_api_url=API_URL, poll_interval=1, process_timeout=10,
        )
        respx.post(TOKEN_ENDPOINT).mock(return_value=_token_response())
        poll_route = respx.get(f"{A2A_URL}/messages/feed").mock(
            return_value=httpx.Response(200, json={"messages": []}))

        with patch("computer.daemon.discover_license_id") as mock_discover:
            mock_discover.return_value = "lic-e2e-test"
            daemon = Daemon(config)

        assert daemon._token_manager is not None

        async def stop_after():
            await asyncio.sleep(1.5)
            daemon.shutdown()
        asyncio.create_task(stop_after())
        await asyncio.wait_for(daemon.run(), timeout=5.0)

        assert poll_route.called
        _assert_bearer(poll_route.calls[0].request)

    @respx.mock
    async def test_token_manager_obtains_jwt(self):
        """TokenManager obtains JWT from operator-token endpoint."""
        token_route = respx.post(TOKEN_ENDPOINT).mock(
            return_value=_token_response())

        from computer.auth import TokenManager
        mgr = TokenManager(paircoder_api_url=API_URL,
                           license_id="lic-e2e-test", operator="mike")
        token = await mgr.get_token()
        await mgr.close()

        assert token == JWT_TOKEN
        body = json.loads(token_route.calls[0].request.content)
        assert body["license_id"] == "lic-e2e-test"
        assert body["operator"] == "mike"

    @respx.mock
    async def test_a2a_accepts_jwt_200_not_401(self, config_with_license):
        """A2A returns 200 on poll (not 401) when JWT is valid."""
        respx.post(TOKEN_ENDPOINT).mock(return_value=_token_response())
        poll_route = respx.get(f"{A2A_URL}/messages/feed").mock(
            return_value=httpx.Response(200, json={"messages": []}))

        daemon = Daemon(config_with_license)
        async def stop_after():
            await asyncio.sleep(1.5)
            daemon.shutdown()
        asyncio.create_task(stop_after())
        await asyncio.wait_for(daemon.run(), timeout=5.0)

        assert poll_route.calls[0].response.status_code == 200

    @respx.mock
    async def test_dispatch_result_posted_with_valid_jwt(self, config_with_license):
        """Dispatch result posted back to A2A with valid JWT."""
        routes = _mock_a2a_with_dispatch()
        await _run_daemon_with_dispatch(config_with_license)

        result_posts = [
            c for c in routes["messages"].calls
            if json.loads(c.request.content).get("type") == "dispatch-result"
        ]
        assert len(result_posts) >= 1
        _assert_bearer(result_posts[0].request)

        body = json.loads(result_posts[0].request.content)
        assert body["operator"] == "mike"
        assert json.loads(body["content"])["success"] is True

    @respx.mock
    async def test_operator_routing_matches_dispatch(self, config_with_license):
        """Test dispatch from CC reaches daemon — operator routing matches."""
        routes = _mock_a2a_with_dispatch()
        await _run_daemon_with_dispatch(config_with_license)

        assert routes["ack"].called
        ack_body = json.loads(routes["ack"].calls[0].request.content)
        assert ack_body["message_id"] == "msg-jwt-1"

        # Verify routing params in poll URL
        url_str = str(routes["poll"].calls[0].request.url)
        assert "operator=mike" in url_str
        assert "workspace=bpsai" in url_str
