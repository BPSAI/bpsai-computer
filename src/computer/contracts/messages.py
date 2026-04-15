"""Pydantic models for all A2A message types.

Existing types: dispatch, resume, dispatch-result, session lifecycle,
session-output, signal batch, heartbeat.

Phase C types: plan-proposal, driver-status, review-result, session-resume.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# -- Channel envelope (wraps all messages) -----------------------------------


class ChannelEnvelope(BaseModel):
    """Envelope for all channel messages sent via POST /messages."""

    type: str = Field(..., max_length=64)
    from_project: str = Field(..., max_length=128)
    to_project: str = Field(..., max_length=128)
    content: str = Field(..., max_length=10_000)
    severity: str | None = Field(None, max_length=32)
    metadata: dict = Field(default_factory=dict)
    operator: str | None = Field(None, max_length=64)
    org_id: str | None = Field(None, max_length=128)
    workspace: str | None = Field(None, max_length=64)


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
    payload: dict = Field(default_factory=dict)
    source: str = Field("", max_length=64)
    signal_id: str | None = Field(None, max_length=128)


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
    metadata: dict = Field(default_factory=dict)


# -- Phase C message types (new) --------------------------------------------


class PlanProposalContent(BaseModel):
    """Content of a plan-proposal message (Navigator -> CC)."""

    plan_id: str = Field(..., max_length=128)
    title: str = Field(..., max_length=256)
    tasks: list[str] = Field(default_factory=list)
    estimated_budget: int = Field(..., ge=0)


class DriverStatusContent(BaseModel):
    """Content of a driver-status message (Driver -> CC)."""

    session_id: str = Field(..., max_length=256)
    task_id: str = Field(..., max_length=64)
    status: str = Field(..., max_length=32)
    progress_pct: int | None = Field(None, ge=0, le=100)
    current_step: str | None = Field(None, max_length=500)


class ReviewResultContent(BaseModel):
    """Content of a review-result message (Reviewer -> CC)."""

    session_id: str = Field(..., max_length=256)
    task_id: str = Field(..., max_length=64)
    verdict: str = Field(..., max_length=32)
    comments: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


class SessionResumeContent(BaseModel):
    """Content of a session-resume message (CC -> daemon)."""

    session_id: str = Field(..., max_length=256)
    reason: str = Field(..., max_length=1000)
    resumed_from: str | None = Field(None, max_length=256)
