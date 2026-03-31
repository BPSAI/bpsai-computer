"""Tests for CDF.1: Input validation + operator fix."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from computer.config import DaemonConfig
from computer.dispatcher import parse_dispatch, parse_resume


@pytest.fixture
def config(tmp_path):
    return DaemonConfig(
        operator="mike",
        workspace="bpsai",
        workspace_root=str(tmp_path),
        a2a_url="http://localhost:9999",
        poll_interval=1,
        process_timeout=10,
    )


# ── Operator check: missing operator -> rejected ──────────────────


class TestOperatorCheckInverted:
    """Missing operator field must cause rejection, not bypass."""

    @pytest.fixture
    def daemon(self, config):
        from computer.daemon import Daemon
        d = Daemon(config)
        d.a2a = AsyncMock()
        d.a2a.poll_dispatches = AsyncMock(return_value=[])
        d.a2a.ack_message = AsyncMock()
        d.a2a.post_result = AsyncMock()
        d.a2a.post_lifecycle = AsyncMock()
        d.a2a.post_session_output = AsyncMock()
        d.a2a.heartbeat = AsyncMock()
        return d

    async def test_resume_with_missing_operator_is_rejected(self, daemon, config, tmp_path):
        """Resume message with no operator field should be rejected."""
        repo_dir = tmp_path / "bpsai-a2a"
        repo_dir.mkdir()

        raw_msg = {
            "id": "msg-r1",
            "type": "resume",
            "content": json.dumps({
                "session_id": "sess-abc",
                "target": "bpsai-a2a",
            }),
        }

        with patch("computer.dispatcher.asyncio.create_subprocess_exec") as mock_exec:
            await daemon._process_resume(raw_msg)
            mock_exec.assert_not_called()

        daemon.a2a.post_lifecycle.assert_not_called()

    async def test_resume_with_empty_operator_is_rejected(self, daemon, config, tmp_path):
        """Resume message with empty operator should be rejected."""
        repo_dir = tmp_path / "bpsai-a2a"
        repo_dir.mkdir()

        raw_msg = {
            "id": "msg-r1",
            "type": "resume",
            "operator": "",
            "content": json.dumps({
                "session_id": "sess-abc",
                "target": "bpsai-a2a",
            }),
        }

        with patch("computer.dispatcher.asyncio.create_subprocess_exec") as mock_exec:
            await daemon._process_resume(raw_msg)
            mock_exec.assert_not_called()

        daemon.a2a.post_lifecycle.assert_not_called()


# ── Path traversal guard ──────────────────────────────────────────


class TestPathTraversalGuard:
    """Path traversal via target field must be rejected."""

    def test_resume_with_path_traversal_target_rejected(self):
        raw = {
            "id": "msg-r1",
            "type": "resume",
            "content": json.dumps({
                "session_id": "sess-abc",
                "target": "../../../etc",
            }),
        }
        with pytest.raises(ValueError, match="[Ii]nvalid target"):
            parse_resume(raw)

    def test_dispatch_with_path_traversal_target_rejected(self):
        raw = {
            "id": "msg-d1",
            "type": "dispatch",
            "content": json.dumps({
                "agent": "driver",
                "target": "../../etc/passwd",
                "prompt": "hack",
            }),
        }
        with pytest.raises(ValueError, match="[Ii]nvalid target"):
            parse_dispatch(raw)

    def test_resume_with_dotdot_in_target_rejected(self):
        raw = {
            "id": "msg-r2",
            "type": "resume",
            "content": json.dumps({
                "session_id": "sess-abc",
                "target": "repo/../../../etc",
            }),
        }
        with pytest.raises(ValueError, match="[Ii]nvalid target"):
            parse_resume(raw)

    def test_dispatch_with_valid_target_accepted(self):
        raw = {
            "id": "msg-d2",
            "type": "dispatch",
            "content": json.dumps({
                "agent": "driver",
                "target": "bpsai-a2a",
                "prompt": "do work",
            }),
        }
        msg = parse_dispatch(raw)
        assert msg.target == "bpsai-a2a"

    def test_resume_with_valid_target_accepted(self):
        raw = {
            "id": "msg-r3",
            "type": "resume",
            "content": json.dumps({
                "session_id": "sess-abc-123",
                "target": "bpsai-a2a",
            }),
        }
        msg = parse_resume(raw)
        assert msg.target == "bpsai-a2a"


# ── session_id regex validation ───────────────────────────────────


class TestSessionIdValidation:
    """session_id must match ^[a-zA-Z0-9\\-_]{1,256}$."""

    def test_resume_with_injection_session_id_rejected(self):
        raw = {
            "id": "msg-r1",
            "type": "resume",
            "content": json.dumps({
                "session_id": "abc --output /tmp/pwned",
                "target": "bpsai-a2a",
            }),
        }
        with pytest.raises(ValueError, match="[Ii]nvalid session_id"):
            parse_resume(raw)

    def test_resume_with_shell_metachar_session_id_rejected(self):
        raw = {
            "id": "msg-r2",
            "type": "resume",
            "content": json.dumps({
                "session_id": "sess;rm -rf /",
                "target": "bpsai-a2a",
            }),
        }
        with pytest.raises(ValueError, match="[Ii]nvalid session_id"):
            parse_resume(raw)

    def test_resume_with_valid_session_id_accepted(self):
        raw = {
            "id": "msg-r3",
            "type": "resume",
            "content": json.dumps({
                "session_id": "sess-abc-123_xyz",
                "target": "bpsai-a2a",
            }),
        }
        msg = parse_resume(raw)
        assert msg.session_id == "sess-abc-123_xyz"

    def test_resume_with_overlong_session_id_rejected(self):
        raw = {
            "id": "msg-r4",
            "type": "resume",
            "content": json.dumps({
                "session_id": "a" * 257,
                "target": "bpsai-a2a",
            }),
        }
        with pytest.raises(ValueError, match="[Ii]nvalid session_id"):
            parse_resume(raw)


# ── target regex validation ───────────────────────────────────────


class TestTargetValidation:
    """target must match ^[a-zA-Z0-9\\-_.]{1,128}$."""

    def test_dispatch_with_slash_in_target_rejected(self):
        raw = {
            "id": "msg-d1",
            "type": "dispatch",
            "content": json.dumps({
                "agent": "driver",
                "target": "repo/subdir",
                "prompt": "work",
            }),
        }
        with pytest.raises(ValueError, match="[Ii]nvalid target"):
            parse_dispatch(raw)

    def test_resume_with_space_in_target_rejected(self):
        raw = {
            "id": "msg-r1",
            "type": "resume",
            "content": json.dumps({
                "session_id": "sess-abc",
                "target": "repo name",
            }),
        }
        with pytest.raises(ValueError, match="[Ii]nvalid target"):
            parse_resume(raw)

    def test_target_with_dots_and_hyphens_accepted(self):
        raw = {
            "id": "msg-d2",
            "type": "dispatch",
            "content": json.dumps({
                "agent": "driver",
                "target": "bpsai-a2a.v2",
                "prompt": "work",
            }),
        }
        msg = parse_dispatch(raw)
        assert msg.target == "bpsai-a2a.v2"

    def test_overlong_target_rejected(self):
        raw = {
            "id": "msg-d3",
            "type": "dispatch",
            "content": json.dumps({
                "agent": "driver",
                "target": "a" * 129,
                "prompt": "work",
            }),
        }
        with pytest.raises(ValueError, match="[Ii]nvalid target"):
            parse_dispatch(raw)
