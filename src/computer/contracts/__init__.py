"""Shared message schema definitions for A2A communication.

Single source of truth for all message types exchanged between
Command Center, daemon (bpsai-computer), and A2A backend.
"""

from computer.contracts.messages import (
    ChannelEnvelope,
    DispatchContent,
    DispatchResultContent,
    DriverStatusContent,
    HeartbeatRequest,
    OutputLine,
    PlanProposalContent,
    ResumeContent,
    ReviewResultContent,
    SessionCompleteContent,
    SessionFailedContent,
    SessionOutputContent,
    SessionResumeContent,
    SessionStartedContent,
    SignalBatchItem,
    SignalBatchRequest,
)
from computer.contracts.schema_export import all_schemas

__all__ = [
    "ChannelEnvelope",
    "DispatchContent",
    "DispatchResultContent",
    "DriverStatusContent",
    "HeartbeatRequest",
    "OutputLine",
    "PlanProposalContent",
    "ResumeContent",
    "ReviewResultContent",
    "SessionCompleteContent",
    "SessionFailedContent",
    "SessionOutputContent",
    "SessionResumeContent",
    "SessionStartedContent",
    "SignalBatchItem",
    "SignalBatchRequest",
    "all_schemas",
]
