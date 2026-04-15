"""Tests for existing A2A message schemas (contracts)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from computer.contracts import (
    ChannelEnvelope,
    DispatchContent,
    DispatchResultContent,
    HeartbeatRequest,
    OutputLine,
    ResumeContent,
    SessionCompleteContent,
    SessionFailedContent,
    SessionOutputContent,
    SessionStartedContent,
    SignalBatchItem,
    SignalBatchRequest,
)


class TestDispatchContent:
    def test_valid_structured(self):
        msg = DispatchContent(agent="driver", target="bpsai-computer", prompt="Do the thing")
        assert msg.agent == "driver"
        assert msg.target == "bpsai-computer"
        assert msg.prompt == "Do the thing"

    def test_agent_defaults_to_driver(self):
        msg = DispatchContent(target="bpsai-a2a", prompt="Fix it")
        assert msg.agent == "driver"

    def test_target_required(self):
        with pytest.raises(ValidationError):
            DispatchContent(prompt="Fix it")

    def test_prompt_required(self):
        with pytest.raises(ValidationError):
            DispatchContent(target="bpsai-a2a")


class TestResumeContent:
    def test_valid(self):
        msg = ResumeContent(session_id="abc123", target="bpsai-computer")
        assert msg.session_id == "abc123"
        assert msg.target == "bpsai-computer"

    def test_session_id_required(self):
        with pytest.raises(ValidationError):
            ResumeContent(target="bpsai-computer")


class TestDispatchResultContent:
    def test_valid(self):
        msg = DispatchResultContent(dispatch_id="d-1", success=True, output="Done")
        assert msg.dispatch_id == "d-1"
        assert msg.success is True

    def test_success_required(self):
        with pytest.raises(ValidationError):
            DispatchResultContent(dispatch_id="d-1", output="Done")


class TestSessionStartedContent:
    def test_valid(self):
        msg = SessionStartedContent(
            session_id="s-1", operator="mike", machine="laptop",
            workspace="bpsai", command="claude -p hello",
            timestamp="2026-04-14T12:00:00Z",
        )
        assert msg.session_id == "s-1"
        assert msg.resumed is False

    def test_resumed_flag(self):
        msg = SessionStartedContent(
            session_id="s-1", operator="mike", machine="laptop",
            workspace="bpsai", command="claude --resume s-1",
            timestamp="2026-04-14T12:00:00Z", resumed=True,
        )
        assert msg.resumed is True


class TestSessionCompleteContent:
    def test_valid(self):
        msg = SessionCompleteContent(
            session_id="s-1", exit_code=0, duration_seconds=42.5,
            output_summary="All done", timestamp="2026-04-14T12:00:00Z",
        )
        assert msg.exit_code == 0
        assert msg.duration_seconds == 42.5


class TestSessionFailedContent:
    def test_valid(self):
        msg = SessionFailedContent(
            session_id="s-1", error="Boom", exit_code=1,
            timestamp="2026-04-14T12:00:00Z",
        )
        assert msg.error == "Boom"

    def test_exit_code_nullable(self):
        msg = SessionFailedContent(
            session_id="s-1", error="Boom", exit_code=None,
            timestamp="2026-04-14T12:00:00Z",
        )
        assert msg.exit_code is None


class TestSessionOutputContent:
    def test_valid(self):
        msg = SessionOutputContent(
            session_id="s-1",
            lines=[OutputLine(line_number=1, content="hello", stream="stdout", timestamp="2026-04-14T12:00:00Z")],
        )
        assert len(msg.lines) == 1
        assert msg.lines[0].stream == "stdout"


class TestSignalBatchItem:
    def test_valid(self):
        item = SignalBatchItem(
            signal_type="test-pass", severity="low",
            timestamp="2026-04-14T12:00:00Z", payload={"count": 42},
        )
        assert item.signal_type == "test-pass"
        assert item.source == ""

    def test_with_signal_id(self):
        item = SignalBatchItem(
            signal_type="test-pass", severity="low",
            timestamp="2026-04-14T12:00:00Z", payload={}, signal_id="abc123",
        )
        assert item.signal_id == "abc123"


class TestSignalBatchRequest:
    def test_valid(self):
        req = SignalBatchRequest(
            operator="mike", repo="bpsai-a2a",
            signals=[SignalBatchItem(signal_type="ci-pass", severity="low", timestamp="2026-04-14T12:00:00Z", payload={})],
        )
        assert req.operator == "mike"
        assert len(req.signals) == 1


class TestHeartbeatRequest:
    def test_valid(self):
        req = HeartbeatRequest(state="running", current_task="Polling", interval_minutes=1)
        assert req.state == "running"

    def test_defaults(self):
        req = HeartbeatRequest(state="idle")
        assert req.current_task is None
        assert req.interval_minutes == 10
        assert req.metadata == {}


class TestChannelEnvelope:
    def test_valid(self):
        env = ChannelEnvelope(
            type="dispatch", from_project="bpsai-command-center",
            to_project="computer",
            content='{"agent":"driver","target":"bpsai-computer","prompt":"go"}',
            operator="mike", workspace="bpsai",
        )
        assert env.type == "dispatch"
        assert env.severity == "info"
        assert env.metadata == {}
