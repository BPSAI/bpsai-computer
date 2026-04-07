"""Local data types for Computer hooks.

Minimal types so hooks do not depend on bpsai-framework engine internals.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class DecisionType(Enum):
    """Types of CNS decisions."""

    DISPATCH = "dispatch"
    DEFER = "defer"
    PRESCRIBE = "prescribe"
    ESCALATE = "escalate"
    CLOSE = "close"


@dataclass
class CNSDecision:
    """A single CNS decision record."""

    decision_id: str
    timestamp: str
    decision_type: DecisionType
    observation: str
    diagnosis: str
    prescription: str
    expected_outcome: str
    actual_outcome: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict."""
        return {
            "decision_id": self.decision_id,
            "timestamp": self.timestamp,
            "decision_type": self.decision_type.value,
            "observation": self.observation,
            "diagnosis": self.diagnosis,
            "prescription": self.prescription,
            "expected_outcome": self.expected_outcome,
            "actual_outcome": self.actual_outcome,
        }


@dataclass
class SprintCompletion:
    """Describes a completed sprint for a single repo."""

    repo_key: str
    sprint_name: str
    test_count: int
    shipped_items: list[str] | None = None

    def __post_init__(self) -> None:
        if self.shipped_items is None:
            self.shipped_items = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo_key": self.repo_key,
            "sprint_name": self.sprint_name,
            "test_count": self.test_count,
            "shipped_items": list(self.shipped_items or []),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SprintCompletion:
        return cls(
            repo_key=data["repo_key"],
            sprint_name=data["sprint_name"],
            test_count=int(data["test_count"]),
            shipped_items=data.get("shipped_items", []),
        )
