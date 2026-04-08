"""Integration tests: full poll → dispatch → ack → result flow with mock A2A."""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

from computer.config import DaemonConfig
from computer.daemon import Daemon


BASE = "http://localhost:9999"


@pytest.fixture
def workspace(tmp_path):
    """Create a workspace with a target repo dir."""
    repo = tmp_path / "bpsai-a2a"
    repo.mkdir()
    return tmp_path


@pytest.fixture
def config(workspace):
    return DaemonConfig(
        operator="mike",
        workspace="bpsai",
        workspace_root=str(workspace),
        a2a_url=BASE,
        poll_interval=1,
        process_timeout=10,
        license_id="lic-test",
    )


def _dispatch_message(msg_id="msg-1", agent="security-auditor", target="bpsai-a2a", prompt="audit this repo"):
    return {
        "id": msg_id,
        "type": "dispatch",
        "operator": "mike",
        "workspace": "bpsai",
        "content": json.dumps({"agent": agent, "target": target, "prompt": prompt}),
        "sender": "command-center",
        "created_at": "2026-03-30T00:00:00Z",
    }


class TestFullDispatchFlow:
    """Test the complete poll → ack → execute → post result flow."""

    @respx.mock
    async def test_poll_dispatch_ack_result(self, config, workspace):
        """Daemon polls, gets a dispatch, acks it, executes, and posts result."""
        # Mock A2A endpoints
        poll_calls = [0]

        def poll_side_effect(request):
            poll_calls[0] += 1
            if poll_calls[0] == 1:
                return httpx.Response(200, json={"messages": [_dispatch_message()]})
            return httpx.Response(200, json={"messages": []})

        poll_route = respx.get(f"{BASE}/messages/feed").mock(side_effect=poll_side_effect)
        ack_route = respx.post(f"{BASE}/messages/ack").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        result_route = respx.post(f"{BASE}/messages").mock(
            return_value=httpx.Response(201, json={"id": "result-1"})
        )
        heartbeat_route = respx.post(f"{BASE}/agents/bpsai-computer/heartbeat").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )

        # Mock Claude Code subprocess (line-by-line reading)
        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(side_effect=[b"Audit complete. 0 issues.\n", b""])
        mock_stderr = AsyncMock()
        mock_stderr.readline = AsyncMock(side_effect=[b""])

        mock_proc = AsyncMock()
        mock_proc.stdout = mock_stdout
        mock_proc.stderr = mock_stderr
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = 0

        daemon = Daemon(config)

        with patch("computer.dispatcher.asyncio.create_subprocess_exec", return_value=mock_proc):
            # Run daemon briefly then stop
            async def stop_after():
                await asyncio.sleep(2.5)
                daemon.shutdown()

            asyncio.create_task(stop_after())
            await asyncio.wait_for(daemon.run(), timeout=10.0)

        # Verify: poll was called
        assert poll_route.called

        # Verify: ack was sent
        assert ack_route.called
        ack_body = json.loads(ack_route.calls[0].request.content)
        assert ack_body["message_id"] == "msg-1"

        # Verify: result was posted
        assert result_route.called
        result_body = next(json.loads(call.request.content) for call in result_route.calls if json.loads(call.request.content).get("type") == "dispatch-result")
        assert result_body["type"] == "dispatch-result"
        assert result_body["operator"] == "mike"
        assert result_body["workspace"] == "bpsai"
        result_content = json.loads(result_body["content"])
        assert result_content["success"] is True
        assert "Audit complete" in result_content["output"]


class TestOperatorFiltering:
    """Test that daemon only processes messages for its operator/workspace."""

    @respx.mock
    async def test_ignores_other_operator_messages(self, config):
        """Messages are filtered by the A2A query params, not client-side."""
        # The daemon sends operator=mike&workspace=bpsai in the query.
        # If A2A returns an empty list, daemon does nothing.
        respx.get(f"{BASE}/messages/feed").mock(
            return_value=httpx.Response(200, json={"messages": []})
        )

        daemon = Daemon(config)

        async def stop_after():
            await asyncio.sleep(1.5)
            daemon.shutdown()

        asyncio.create_task(stop_after())
        await asyncio.wait_for(daemon.run(), timeout=5.0)

        # Verify query params include correct operator/workspace filtering
        request = respx.calls[0].request
        url_str = str(request.url)
        assert "operator=mike" in url_str
        assert "workspace=bpsai" in url_str
        assert "agent=computer" in url_str


class TestMissingRepoError:
    """Test that missing target repo returns an error result."""

    @respx.mock
    async def test_missing_repo_posts_error(self, config):
        """When target repo doesn't exist, daemon posts error result."""
        respx.get(f"{BASE}/messages/feed").mock(
            side_effect=[
                httpx.Response(200, json={"messages": [_dispatch_message(target="nonexistent-repo")]}),
                httpx.Response(200, json={"messages": []}),
            ]
        )
        ack_route = respx.post(f"{BASE}/messages/ack").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        result_route = respx.post(f"{BASE}/messages").mock(
            return_value=httpx.Response(201, json={"id": "err-1"})
        )
        respx.post(f"{BASE}/agents/bpsai-computer/heartbeat").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )

        daemon = Daemon(config)

        async def stop_after():
            await asyncio.sleep(2.5)
            daemon.shutdown()

        asyncio.create_task(stop_after())
        await asyncio.wait_for(daemon.run(), timeout=10.0)

        # Verify: error result was posted
        assert result_route.called
        result_body = next(json.loads(call.request.content) for call in result_route.calls if json.loads(call.request.content).get("type") == "dispatch-result")
        result_content = json.loads(result_body["content"])
        assert result_content["success"] is False
        assert "not found" in result_content["output"].lower()
