"""Shared message schema definitions for A2A communication.

Single source of truth for all message types exchanged between
Command Center, daemon (bpsai-computer), and A2A backend.
"""

from computer.contracts.messages import (
    SEVERITY_LEVELS,
    SEVERITY_ORDER,
    ChannelEnvelope,
    DispatchContent,
    DispatchResultContent,
    DriverStatusContent,
    HeartbeatRequest,
    OutputLine,
    PermissionRequestContent,
    PermissionResponseContent,
    PlanProposalContent,
    ResumeContent,
    ReviewResultContent,
    Severity,
    SessionCompleteContent,
    SessionFailedContent,
    SessionOutputContent,
    SessionResumeContent,
    SessionStartedContent,
    SignalBatchItem,
    SignalBatchRequest,
    severities_at_or_above,
)
from computer.contracts.schema_export import all_schemas

__all__ = [
    "SEVERITY_LEVELS",
    "SEVERITY_ORDER",
    "ChannelEnvelope",
    "DispatchContent",
    "DispatchResultContent",
    "DriverStatusContent",
    "HeartbeatRequest",
    "OutputLine",
    "PermissionRequestContent",
    "PermissionResponseContent",
    "PlanProposalContent",
    "ResumeContent",
    "ReviewResultContent",
    "Severity",
    "SessionCompleteContent",
    "SessionFailedContent",
    "SessionOutputContent",
    "SessionResumeContent",
    "SessionStartedContent",
    "SignalBatchItem",
    "SignalBatchRequest",
    "all_schemas",
    "severities_at_or_above",
]
