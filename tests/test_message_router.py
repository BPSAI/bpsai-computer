"""Tests for daemon message type router (T2I.8)."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

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


# ── Registry structure ─────────────────────────────────────────────


class TestMessageTypeRegistry:
    """Dispatcher has a registry of message type handlers."""

    def test_daemon_has_message_handlers_registry(self, daemon):
        """Daemon exposes a _message_handlers dict."""
        assert hasattr(daemon, "_message_handlers")
        assert isinstance(daemon._message_handlers, dict)

    def test_dispatch_handler_registered(self, daemon):
        """dispatch type is registered by default."""
        assert "dispatch" in daemon._message_handlers

    def test_resume_handler_registered(self, daemon):
        """resume type is registered by default."""
        assert "resume" in daemon._message_handlers

    def test_register_custom_handler(self, daemon):
        """Adding a new message type is: define handler + register it."""
        async def handle_plan_proposal(raw_msg: dict) -> None:
            pass

        daemon.register_message_handler("plan-proposal", handle_plan_proposal)
        assert "plan-proposal" in daemon._message_handlers
        assert daemon._message_handlers["plan-proposal"] is handle_plan_proposal

    def test_register_overwrites_existing(self, daemon):
        """Re-registering a type replaces the previous handler."""
        async def new_dispatch_handler(raw_msg: dict) -> None:
            pass

        daemon.register_message_handler("dispatch", new_dispatch_handler)
        assert daemon._message_handlers["dispatch"] is new_dispatch_handler


# ── Helpers ────────────────────────────────────────────────────────


async def _run_daemon_with_messages(daemon, messages: list[dict]) -> None:
    """Feed messages into daemon's poll loop once, then shut down."""
    call_count = [0]

    async def mock_poll():
        call_count[0] += 1
        if call_count[0] == 1:
            return messages
        return []

    daemon.a2a.poll_dispatches = AsyncMock(side_effect=mock_poll)

    async def stop_after():
        await asyncio.sleep(0.5)
        daemon.shutdown()

    asyncio.create_task(stop_after())
    await asyncio.wait_for(daemon.run(), timeout=5.0)


# ── Routing ────────────────────────────────────────────────────────


class TestMessageRouting:
    """Run loop routes messages through the registry."""

    async def test_dispatch_message_routes_to_dispatch_handler(self, daemon):
        """A message with type=dispatch routes to _process_dispatch."""
        daemon._process_dispatch = AsyncMock()
        raw_msg = {"id": "msg-1", "type": "dispatch", "content": "hello"}
        await _run_daemon_with_messages(daemon, [raw_msg])
        daemon._process_dispatch.assert_called_once_with(raw_msg)

    async def test_resume_message_routes_to_resume_handler(self, daemon):
        """A message with type=resume routes to _process_resume."""
        daemon._process_resume = AsyncMock()
        raw_msg = {
            "id": "msg-r1",
            "type": "resume",
            "operator": "mike",
            "content": json.dumps({"session_id": "sess-1", "target": "bpsai-a2a"}),
        }
        await _run_daemon_with_messages(daemon, [raw_msg])
        daemon._process_resume.assert_called_once_with(raw_msg)

    async def test_custom_handler_is_called(self, daemon):
        """A registered custom handler is invoked for its message type."""
        handler = AsyncMock()
        daemon.register_message_handler("plan-proposal", handler)
        raw_msg = {"id": "msg-p1", "type": "plan-proposal", "content": "{}"}
        await _run_daemon_with_messages(daemon, [raw_msg])
        handler.assert_called_once_with(raw_msg)

    async def test_no_type_field_defaults_to_dispatch(self, daemon):
        """Messages without a type field default to dispatch handler."""
        daemon._process_dispatch = AsyncMock()
        raw_msg = {"id": "msg-2", "content": "hello"}
        await _run_daemon_with_messages(daemon, [raw_msg])
        daemon._process_dispatch.assert_called_once_with(raw_msg)

    async def test_missing_id_is_skipped(self, daemon):
        """Messages with empty or missing id are skipped entirely."""
        daemon._process_dispatch = AsyncMock()
        raw_msg = {"type": "dispatch", "content": "hello"}
        await _run_daemon_with_messages(daemon, [raw_msg])
        daemon._process_dispatch.assert_not_called()


# ── Unknown message types ─────────────────────────────────────────


class TestUnknownMessageType:
    """Unknown message types are logged and acked, not dropped or crashed."""

    async def test_unknown_type_is_acked(self, daemon):
        """Unknown message types are acked so they don't re-deliver."""
        raw_msg = {"id": "msg-u1", "type": "alien-message", "content": "{}"}
        await _run_daemon_with_messages(daemon, [raw_msg])
        daemon.a2a.ack_message.assert_called_once_with(
            "msg-u1", response="unsupported_message_type",
        )

    async def test_unknown_type_does_not_crash(self, daemon):
        """Unknown message type followed by a normal message — daemon keeps running."""
        unknown_msg = {"id": "msg-u1", "type": "alien-message", "content": "{}"}
        dispatch_msg = {"id": "msg-d1", "type": "dispatch", "content": "hello"}
        daemon._process_dispatch = AsyncMock()
        await _run_daemon_with_messages(daemon, [unknown_msg, dispatch_msg])
        daemon.a2a.ack_message.assert_any_call(
            "msg-u1", response="unsupported_message_type",
        )
        daemon._process_dispatch.assert_called_once_with(dispatch_msg)

    async def test_unknown_type_is_logged(self, daemon, caplog):
        """Unknown message types produce a warning log."""
        import logging

        raw_msg = {"id": "msg-u1", "type": "alien-message", "content": "{}"}
        with caplog.at_level(logging.WARNING):
            await _run_daemon_with_messages(daemon, [raw_msg])
        assert any("alien-message" in r.message for r in caplog.records)
