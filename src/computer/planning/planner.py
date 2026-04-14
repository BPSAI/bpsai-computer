"""Sprint planner for the Computer PLAN phase.

Reads Metis standup output and execution priorities to produce a
structured SprintBacklog with optional LLM-assisted enrichment.

Key invariant: produces DRAFTS only. Never auto-dispatches.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from computer.planning.parsers import parse_standup, read_execution_priorities
from computer.planning.types import (
    PlanningContext,
    PriorityItem,
    SprintBacklog,
    SprintTask,
    StandupItem,
)

# Re-export for backward compat
__all__ = [
    "SprintBacklog", "SprintTask", "StandupItem", "PriorityItem",
    "PlanningContext", "SprintPlanner", "parse_standup",
    "read_execution_priorities",
]

LLMCallable = Callable[[str, str], str | None]


class SprintPlanner:
    """Sprint planning from standup + priorities to backlog.

    Mechanical mode (no LLM): maps findings to tasks by severity.
    LLM-assisted mode: richer descriptions, acceptance criteria.
    """

    def __init__(self, llm_call: LLMCallable | None = None) -> None:
        self._llm = llm_call

    def plan(
        self, standup_path: Path, priorities_path: Path,
        target_repo: str, sprint_id: str, theme: str, goal: str = "",
    ) -> SprintBacklog:
        """Read inputs and produce a draft SprintBacklog."""
        standup_items = parse_standup(standup_path)
        priority_items = read_execution_priorities(priorities_path)
        tasks = _build_tasks(standup_items, priority_items, sprint_id)

        if self._llm and tasks:
            tasks = _enrich_with_llm(self._llm, tasks, standup_items, theme)

        if not goal:
            goal = _derive_goal(standup_items, theme)

        return SprintBacklog(
            sprint_id=sprint_id, repo=target_repo, theme=theme,
            goal=goal, tasks=tasks, status="draft",
        )


def _build_tasks(
    items: list[StandupItem], priorities: list[PriorityItem], sprint_id: str,
) -> list[SprintTask]:
    """Convert standup findings + priorities into tasks."""
    tasks: list[SprintTask] = []
    seq = 1
    prefix = sprint_id.split("-")[-1] if "-" in sprint_id else sprint_id

    for item in items:
        if item.severity == "high":
            tasks.append(SprintTask(
                task_id=f"T{prefix}.{seq}", title=_title(item.description),
                description=item.description, complexity=15, priority="P0", phase=1,
            ))
            seq += 1
    for item in items:
        if item.severity == "medium":
            tasks.append(SprintTask(
                task_id=f"T{prefix}.{seq}", title=_title(item.description),
                description=item.description, complexity=10, priority="P1", phase=2,
            ))
            seq += 1
    for pi in priorities:
        tasks.append(SprintTask(
            task_id=f"T{prefix}.{seq}", title=pi.item,
            description=f"{pi.item} ({pi.notes})" if pi.notes else pi.item,
            complexity=_parse_effort(pi.effort),
            priority="P0" if pi.tier <= 3 else "P1",
            phase=1 if pi.tier <= 3 else 2,
        ))
        seq += 1
    return tasks


def _enrich_with_llm(
    llm: LLMCallable, tasks: list[SprintTask],
    items: list[StandupItem], theme: str,
) -> list[SprintTask]:
    """Use LLM to improve task descriptions and add AC."""
    system = (
        "You are a sprint planning assistant. Given draft tasks, "
        "improve each description to be actionable and specific. "
        "Add 3-5 acceptance criteria per task. Respond in JSON: "
        '[{"task_id": "...", "description": "...", "acceptance_criteria": ["..."]}]'
    )
    task_lines = "\n".join(
        f"- {t.task_id}: {t.title} (Cx:{t.complexity}, {t.priority})"
        for t in tasks
    )
    context = "\n".join(f"- [{i.severity}] {i.description}" for i in items[:10])
    user = f"Theme: {theme}\n\nFindings:\n{context}\n\nDraft tasks:\n{task_lines}"

    response = llm(system, user)
    if not response:
        return tasks

    try:
        import json
        enrichments = json.loads(response)
        by_id = {e["task_id"]: e for e in enrichments if "task_id" in e}
        for task in tasks:
            if task.task_id in by_id:
                e = by_id[task.task_id]
                if "description" in e:
                    task.description = e["description"]
                if "acceptance_criteria" in e:
                    task.acceptance_criteria = e["acceptance_criteria"]
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return tasks


def _title(description: str) -> str:
    t = description.strip()
    return t[:57] + "..." if len(t) > 60 else t


def _parse_effort(effort_str: str) -> int:
    m = re.search(r"(\d+)", effort_str)
    return int(m.group(1)) if m else 10


def _derive_goal(items: list[StandupItem], theme: str) -> str:
    if items:
        descs = [i.description for i in items[:3]]
        return f"Address {theme.lower()} findings: {'; '.join(descs)}."
    return f"Sprint focused on {theme}."
