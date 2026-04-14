"""Data types for the sprint planner.

Extracted from sprint_planner.py to keep files under 200 lines.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StandupItem:
    """A single actionable item extracted from Metis standup output."""

    source: str
    description: str
    severity: str = "medium"
    hypothesis_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "description": self.description,
            "severity": self.severity,
            "hypothesis_id": self.hypothesis_id,
        }


@dataclass
class PriorityItem:
    """An item from execution-priorities.md with tier ordering."""

    item: str
    repo: str
    effort: str
    tier: int
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "item": self.item,
            "repo": self.repo,
            "effort": self.effort,
            "tier": self.tier,
            "notes": self.notes,
        }


@dataclass
class SprintTask:
    """A single task within a sprint backlog."""

    task_id: str
    title: str
    description: str
    complexity: int
    priority: str
    acceptance_criteria: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    phase: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "complexity": self.complexity,
            "priority": self.priority,
            "acceptance_criteria": list(self.acceptance_criteria),
            "files": list(self.files),
            "phase": self.phase,
        }


@dataclass
class SprintBacklog:
    """A complete sprint backlog ready for rendering and delivery."""

    sprint_id: str
    repo: str
    theme: str
    goal: str
    tasks: list[SprintTask]
    author: str = "Framework Navigator (CNS)"
    date: str = ""
    portfolio_alignment: str = ""
    predecessor: str = ""
    status: str = "draft"

    @property
    def total_complexity(self) -> int:
        return sum(t.complexity for t in self.tasks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sprint_id": self.sprint_id,
            "repo": self.repo,
            "theme": self.theme,
            "goal": self.goal,
            "author": self.author,
            "date": self.date,
            "portfolio_alignment": self.portfolio_alignment,
            "predecessor": self.predecessor,
            "status": self.status,
            "total_complexity": self.total_complexity,
            "tasks": [t.to_dict() for t in self.tasks],
        }


@dataclass
class PlanningContext:
    """Input context for the sprint planner."""

    standup_items: list[StandupItem]
    priority_items: list[PriorityItem] = field(default_factory=list)
    hypothesis_states: dict[str, dict[str, Any]] = field(default_factory=dict)
    target_repo: str = ""
    sprint_prefix: str = ""


# Shared regex patterns
FINDING_RE = re.compile(
    r"^-\s+\[(?P<severity>high|medium|low)\]\s+(?P<desc>.+)$",
    re.IGNORECASE,
)
HYP_ID_RE = re.compile(r"\bHYP-\d+\b")
STALE_RE = re.compile(
    r"^-\s+\*\*(?P<hyp_id>HYP-\d+)\*\*\s*—\s*(?P<desc>.+)$",
)
