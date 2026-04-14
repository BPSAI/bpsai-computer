"""Draft next sprint backlog after sprint completion.

Combines carry-over from failed/deferred tasks with Metis standup
findings to produce a draft SprintBacklog. Status is always "draft" —
never auto-dispatched.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from computer.planning.types import SprintBacklog, SprintTask, StandupItem


class TaskOutcome(Enum):
    DONE = "done"
    FAILED = "failed"
    DEFERRED = "deferred"


_SEVERITY_PRIORITY = {"high": "P0", "medium": "P1", "low": "P2"}
_SEVERITY_COMPLEXITY = {"high": 15, "medium": 10, "low": 5}


@dataclass
class CompletedTask:
    """A task from the just-completed sprint with its outcome."""

    task_id: str
    title: str
    outcome: TaskOutcome
    reason: str = ""
    priority: str = "P1"
    complexity: int = 10

    @property
    def is_carry_over(self) -> bool:
        return self.outcome in (TaskOutcome.FAILED, TaskOutcome.DEFERRED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "outcome": self.outcome.value,
            "reason": self.reason,
            "priority": self.priority,
            "complexity": self.complexity,
        }


@dataclass
class NextSprintDraft:
    """Result of next-sprint authoring."""

    backlog: SprintBacklog
    carry_over_ids: list[str] = field(default_factory=list)
    metis_task_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "backlog": self.backlog.to_dict(),
            "carry_over_ids": list(self.carry_over_ids),
            "metis_task_ids": list(self.metis_task_ids),
        }


class NextSprintAuthor:
    """Drafts the next sprint backlog from completion data + Metis."""

    def plan_next(
        self,
        completed_tasks: list[CompletedTask],
        standup_items: list[StandupItem],
        target_repo: str,
        next_sprint_id: str,
        theme: str,
        goal: str = "",
        predecessor: str = "",
    ) -> NextSprintDraft:
        prefix = _extract_prefix(next_sprint_id)
        seq = 1
        tasks: list[SprintTask] = []
        carry_over_ids: list[str] = []
        metis_task_ids: list[str] = []

        for ct in completed_tasks:
            if not ct.is_carry_over:
                continue
            tid = f"T{prefix}.{seq}"
            desc = ct.title
            if ct.reason:
                desc = f"{ct.title} (carry-over: {ct.reason})"
            tasks.append(SprintTask(
                task_id=tid, title=ct.title, description=desc,
                complexity=ct.complexity, priority=ct.priority, phase=1,
            ))
            carry_over_ids.append(tid)
            seq += 1

        for item in standup_items:
            tid = f"T{prefix}.{seq}"
            tasks.append(SprintTask(
                task_id=tid,
                title=_title(item.description),
                description=item.description,
                complexity=_SEVERITY_COMPLEXITY.get(item.severity, 10),
                priority=_SEVERITY_PRIORITY.get(item.severity, "P1"),
                phase=2,
            ))
            metis_task_ids.append(tid)
            seq += 1

        if not goal:
            goal = _derive_goal(carry_over_ids, standup_items, theme)

        backlog = SprintBacklog(
            sprint_id=next_sprint_id,
            repo=target_repo,
            theme=theme,
            goal=goal,
            tasks=tasks,
            predecessor=predecessor,
            status="draft",
        )

        return NextSprintDraft(
            backlog=backlog,
            carry_over_ids=carry_over_ids,
            metis_task_ids=metis_task_ids,
        )


def _extract_prefix(sprint_id: str) -> str:
    """Extract numeric suffix for task IDs: S11 -> 11, Bot-S34 -> S34."""
    import re
    m = re.search(r"(\d[\w.]*)$", sprint_id)
    return m.group(1) if m else sprint_id


def _title(description: str) -> str:
    t = description.strip()
    return t[:57] + "..." if len(t) > 60 else t


def _derive_goal(
    carry_ids: list[str], items: list[StandupItem], theme: str,
) -> str:
    parts: list[str] = []
    if carry_ids:
        parts.append(f"resolve {len(carry_ids)} carried-over tasks")
    if items:
        parts.append(f"address {len(items)} Metis findings")
    if parts:
        return f"{theme}: {', '.join(parts)}."
    return f"Sprint focused on {theme}."
