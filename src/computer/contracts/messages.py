"""Pydantic models for all A2A message types.

Existing types: dispatch, resume, dispatch-result, session lifecycle,
session-output, signal batch, heartbeat.

Phase C types: plan-proposal, driver-status, review-result, session-resume.
"""

from __future__ import annotations

import json as _json
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


# -- Severity levels -----------------------------------------------------------


class Severity(StrEnum):
    """Message severity levels, ordered from least to most severe."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


SEVERITY_LEVELS: set[str] = {s.value for s in Severity}

SEVERITY_ORDER: dict[str, int] = {s.value: i for i, s in enumerate(Severity)}


def severities_at_or_above(min_severity: str) -> set[str]:
    """Return all severity levels at or above the given threshold."""
    threshold = SEVERITY_ORDER.get(min_severity)
    if threshold is None:
        raise ValueError(f"Unknown severity: {min_severity!r}")
    return {s for s, rank in SEVERITY_ORDER.items() if rank >= threshold}


# -- Channel envelope (wraps all messages) -----------------------------------


_MAX_DICT_BYTES = 4096


def _validate_dict_size(v: dict[str, Any], field_name: str = "dict") -> dict[str, Any]:
    """Reject dicts whose JSON serialisation exceeds _MAX_DICT_BYTES."""
    raw = _json.dumps(v, separators=(",", ":"), default=str)
    if len(raw.encode()) > _MAX_DICT_BYTES:
        raise ValueError(
            f"{field_name} exceeds {_MAX_DICT_BYTES}-byte limit "
            f"({len(raw.encode())} bytes)"
        )
    return v


def _validate_severity(v: str) -> str:
    if v not in SEVERITY_LEVELS:
        raise ValueError(f"severity must be one of {sorted(SEVERITY_LEVELS)}, got {v!r}")
    return v


class ChannelEnvelope(BaseModel):
    """Envelope for all channel messages sent via POST /messages."""

    type: str = Field(..., max_length=64)
    from_project: str = Field(..., max_length=128)
    to_project: str = Field(..., max_length=128)
    content: str = Field(..., max_length=10_000)
    severity: str = Field("info", max_length=32)
    metadata: dict[str, Any] = Field(default_factory=dict)
    operator: str | None = Field(None, max_length=64)
    org_id: str | None = Field(None, max_length=128)
    workspace: str | None = Field(None, max_length=64)

    @field_validator("severity")
    @classmethod
    def check_severity(cls, v: str) -> str:
        return _validate_severity(v)

    @field_validator("metadata")
    @classmethod
    def check_metadata_size(cls, v: dict[str, Any]) -> dict[str, Any]:
        return _validate_dict_size(v, "metadata")


# -- Existing message content types -----------------------------------------


class DispatchContent(BaseModel):
    """Content of a dispatch message (JSON inside ChannelEnvelope.content)."""

    agent: str = Field("driver", max_length=64)
    target: str = Field(..., max_length=128)
    prompt: str = Field(..., max_length=50_000)


class ResumeContent(BaseModel):
    """Content of a resume message."""

    session_id: str = Field(..., max_length=256)
    target: str = Field(..., max_length=128)


class DispatchResultContent(BaseModel):
    """Content of a dispatch-result message."""

    dispatch_id: str = Field(..., max_length=256)
    success: bool
    output: str = Field(..., max_length=500_000)


class SessionStartedContent(BaseModel):
    """Content of a session-started lifecycle event."""

    session_id: str = Field(..., max_length=256)
    operator: str = Field(..., max_length=64)
    machine: str = Field(..., max_length=128)
    workspace: str = Field(..., max_length=256)
    command: str = Field(..., max_length=10_000)
    timestamp: str = Field(..., max_length=64)
    resumed: bool = False


class SessionCompleteContent(BaseModel):
    """Content of a session-complete lifecycle event."""

    session_id: str = Field(..., max_length=256)
    exit_code: int
    duration_seconds: float
    output_summary: str = Field(..., max_length=50_000)
    timestamp: str = Field(..., max_length=64)


class SessionFailedContent(BaseModel):
    """Content of a session-failed lifecycle event."""

    session_id: str = Field(..., max_length=256)
    error: str = Field(..., max_length=50_000)
    exit_code: int | None
    timestamp: str = Field(..., max_length=64)


class OutputLine(BaseModel):
    """Single line in a session-output batch."""

    line_number: int
    content: str
    stream: str = Field(..., max_length=16)
    timestamp: str = Field(..., max_length=64)


class SessionOutputContent(BaseModel):
    """Content of a session-output streaming message."""

    session_id: str = Field(..., max_length=256)
    lines: list[OutputLine]


# -- Signal batch ------------------------------------------------------------


class SignalBatchItem(BaseModel):
    """Single signal in a batch push."""

    signal_type: str = Field(..., max_length=64)
    severity: str = Field(..., max_length=32)
    timestamp: str = Field(..., max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)
    source: str = Field("", max_length=64)
    signal_id: str | None = Field(None, max_length=128)

    @field_validator("severity")
    @classmethod
    def check_severity(cls, v: str) -> str:
        return _validate_severity(v)

    @field_validator("payload")
    @classmethod
    def check_payload_size(cls, v: dict[str, Any]) -> dict[str, Any]:
        return _validate_dict_size(v, "payload")


class SignalBatchRequest(BaseModel):
    """Envelope for POST /signals/batch."""

    operator: str = Field(..., max_length=64)
    repo: str = Field(..., max_length=256)
    signals: list[SignalBatchItem]


# -- Heartbeat ---------------------------------------------------------------


class HeartbeatRequest(BaseModel):
    """Payload for POST /agents/{name}/heartbeat."""

    state: str = Field(..., max_length=32)
    current_task: str | None = Field(None, max_length=500)
    interval_minutes: int = Field(10, ge=1, le=1440)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def check_metadata_size(cls, v: dict[str, Any]) -> dict[str, Any]:
        return _validate_dict_size(v, "metadata")


# -- Phase C message types (new) --------------------------------------------


class PlanProposalContent(BaseModel):
    """Content of a plan-proposal message (Navigator -> CC)."""

    plan_id: str = Field(..., max_length=128)
    title: str = Field(..., max_length=256)
    tasks: list[str] = Field(default_factory=list)
    estimated_budget: int = Field(..., ge=0)


_VALID_DRIVER_STATUSES = frozenset({"pending", "in_progress", "complete", "failed", "blocked"})


class DriverStatusContent(BaseModel):
    """Content of a driver-status message (Driver -> CC)."""

    session_id: str = Field(..., max_length=256)
    task_id: str = Field(..., max_length=64)
    status: str = Field(..., max_length=32)
    progress_pct: int | None = Field(None, ge=0, le=100)
    current_step: str | None = Field(None, max_length=500)

    @field_validator("status")
    @classmethod
    def check_status(cls, v: str) -> str:
        if v not in _VALID_DRIVER_STATUSES:
            raise ValueError(
                f"status must be one of {sorted(_VALID_DRIVER_STATUSES)}, got {v!r}"
            )
        return v


_VALID_VERDICTS = frozenset({"approved", "changes_requested", "rejected"})


class ReviewResultContent(BaseModel):
    """Content of a review-result message (Reviewer -> CC)."""

    session_id: str = Field(..., max_length=256)
    task_id: str = Field(..., max_length=64)
    verdict: str = Field(..., max_length=32)
    comments: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)

    @field_validator("verdict")
    @classmethod
    def check_verdict(cls, v: str) -> str:
        if v not in _VALID_VERDICTS:
            raise ValueError(
                f"verdict must be one of {sorted(_VALID_VERDICTS)}, got {v!r}"
            )
        return v


class SessionResumeContent(BaseModel):
    """Content of a session-resume message (CC -> daemon)."""

    session_id: str = Field(..., max_length=256)
    reason: str = Field(..., max_length=1000)
    resumed_from: str | None = Field(None, max_length=256)


# -- Permission escalation (T2I.5) -----------------------------------------

_VALID_OPERATIONS = frozenset({"read", "write", "execute"})
_VALID_SCOPES = frozenset({"file", "directory", "glob"})


def _validate_operation(v: str) -> str:
    if v not in _VALID_OPERATIONS:
        raise ValueError(f"operation must be one of {sorted(_VALID_OPERATIONS)}, got {v!r}")
    return v


def _validate_scope(v: str) -> str:
    if v not in _VALID_SCOPES:
        raise ValueError(f"scope must be one of {sorted(_VALID_SCOPES)}, got {v!r}")
    return v


class PermissionRequestContent(BaseModel):
    """Content of a permission-request message (Driver -> CC/operator)."""

    path: str = Field(..., max_length=512)
    operation: str = Field(..., max_length=32)
    reason: str = Field(..., max_length=1000)
    task_id: str = Field(..., max_length=64)

    @field_validator("operation")
    @classmethod
    def check_operation(cls, v: str) -> str:
        return _validate_operation(v)


class PermissionResponseContent(BaseModel):
    """Content of a permission-response message (operator/Navigator -> Driver)."""

    approved: bool
    scope: str = Field(..., max_length=32)
    ttl: int = Field(..., ge=0)
    request_id: str | None = Field(None, max_length=256)

    @field_validator("scope")
    @classmethod
    def check_scope(cls, v: str) -> str:
        return _validate_scope(v)


# -- Workspace listing ---------------------------------------------------------


class WorkspaceInfo(BaseModel):
    """A workspace returned by GET /workspaces."""

    workspace_id: str
    name: str
    workspace_root: str | None = None
    status: str = Field(..., pattern=r"^(active|inactive|archived)$")
