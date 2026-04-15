"""JSON Schema export for cross-repo validation."""

from __future__ import annotations

from computer.contracts.messages import (
    ChannelEnvelope,
    DispatchContent,
    DispatchResultContent,
    DriverStatusContent,
    HeartbeatRequest,
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

_ALL_MODELS = {
    "ChannelEnvelope": ChannelEnvelope,
    "DispatchContent": DispatchContent,
    "ResumeContent": ResumeContent,
    "DispatchResultContent": DispatchResultContent,
    "SessionStartedContent": SessionStartedContent,
    "SessionCompleteContent": SessionCompleteContent,
    "SessionFailedContent": SessionFailedContent,
    "SessionOutputContent": SessionOutputContent,
    "SignalBatchItem": SignalBatchItem,
    "SignalBatchRequest": SignalBatchRequest,
    "HeartbeatRequest": HeartbeatRequest,
    "PlanProposalContent": PlanProposalContent,
    "DriverStatusContent": DriverStatusContent,
    "ReviewResultContent": ReviewResultContent,
    "SessionResumeContent": SessionResumeContent,
}


def all_schemas() -> dict[str, dict]:
    """Return JSON Schema for every contract model.

    Returns a dict mapping model name to its JSON Schema dict.
    Other repos can snapshot or validate against these.
    """
    return {name: cls.model_json_schema() for name, cls in _ALL_MODELS.items()}
