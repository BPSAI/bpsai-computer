"""Tests for security findings SEC-003 and REV-001 on message contracts.

SEC-003: Dict size caps on metadata/payload fields.
REV-001: Enum constraint validators on severity, status, verdict.
REV-001: WorkspaceInfo in schema export.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from computer.contracts.messages import (
    ChannelEnvelope,
    DriverStatusContent,
    HeartbeatRequest,
    ReviewResultContent,
    SignalBatchItem,
    WorkspaceInfo,
)
from computer.contracts.schema_export import all_schemas


# -- SEC-003: Dict size caps --------------------------------------------------


class TestChannelEnvelopeMetadataCap:
    """ChannelEnvelope.metadata rejects dicts exceeding 4096 bytes."""

    def test_small_metadata_accepted(self):
        env = ChannelEnvelope(
            type="dispatch", from_project="a", to_project="b",
            content="hello", metadata={"key": "value"},
        )
        assert env.metadata == {"key": "value"}

    def test_empty_metadata_accepted(self):
        env = ChannelEnvelope(
            type="dispatch", from_project="a", to_project="b",
            content="hello",
        )
        assert env.metadata == {}

    def test_oversized_metadata_rejected(self):
        big = {"k": "x" * 5000}
        with pytest.raises(ValidationError, match="4096-byte limit"):
            ChannelEnvelope(
                type="dispatch", from_project="a", to_project="b",
                content="hello", metadata=big,
            )


class TestSignalBatchItemPayloadCap:
    """SignalBatchItem.payload rejects dicts exceeding 4096 bytes."""

    def test_small_payload_accepted(self):
        item = SignalBatchItem(
            signal_type="test", severity="info",
            timestamp="2026-01-01T00:00:00Z", payload={"ok": True},
        )
        assert item.payload == {"ok": True}

    def test_oversized_payload_rejected(self):
        big = {"k": "x" * 5000}
        with pytest.raises(ValidationError, match="4096-byte limit"):
            SignalBatchItem(
                signal_type="test", severity="info",
                timestamp="2026-01-01T00:00:00Z", payload=big,
            )


class TestHeartbeatMetadataCap:
    """HeartbeatRequest.metadata rejects dicts exceeding 4096 bytes."""

    def test_small_metadata_accepted(self):
        req = HeartbeatRequest(state="running", metadata={"cpu": 0.5})
        assert req.metadata == {"cpu": 0.5}

    def test_oversized_metadata_rejected(self):
        big = {"k": "x" * 5000}
        with pytest.raises(ValidationError, match="4096-byte limit"):
            HeartbeatRequest(state="running", metadata=big)


# -- REV-001: Enum validators -------------------------------------------------


class TestSignalBatchItemSeverityValidator:
    """SignalBatchItem.severity must be a valid SEVERITY_LEVELS value."""

    def test_valid_severities_accepted(self):
        for sev in ("info", "warning", "error", "critical"):
            item = SignalBatchItem(
                signal_type="test", severity=sev,
                timestamp="2026-01-01T00:00:00Z",
            )
            assert item.severity == sev

    def test_invalid_severity_rejected(self):
        with pytest.raises(ValidationError, match="severity"):
            SignalBatchItem(
                signal_type="test", severity="low",
                timestamp="2026-01-01T00:00:00Z",
            )


class TestDriverStatusContentValidator:
    """DriverStatusContent.status must be one of the valid values."""

    def test_valid_statuses_accepted(self):
        for status in ("pending", "in_progress", "complete", "failed", "blocked"):
            msg = DriverStatusContent(
                session_id="s-1", task_id="T1", status=status,
            )
            assert msg.status == status

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError, match="status"):
            DriverStatusContent(
                session_id="s-1", task_id="T1", status="cancelled",
            )


class TestReviewResultContentValidator:
    """ReviewResultContent.verdict must be one of the valid values."""

    def test_valid_verdicts_accepted(self):
        for verdict in ("approved", "changes_requested", "rejected"):
            msg = ReviewResultContent(
                session_id="s-1", task_id="T1", verdict=verdict,
            )
            assert msg.verdict == verdict

    def test_invalid_verdict_rejected(self):
        with pytest.raises(ValidationError, match="verdict"):
            ReviewResultContent(
                session_id="s-1", task_id="T1", verdict="maybe",
            )


# -- REV-001: WorkspaceInfo in schema export -----------------------------------


class TestWorkspaceInfoInSchemaExport:
    """WorkspaceInfo must be present in the schema export."""

    def test_workspace_info_in_all_schemas(self):
        schemas = all_schemas()
        assert "WorkspaceInfo" in schemas

    def test_workspace_info_schema_has_properties(self):
        schemas = all_schemas()
        ws_schema = schemas["WorkspaceInfo"]
        assert "properties" in ws_schema
        assert "workspace_id" in ws_schema["properties"]
