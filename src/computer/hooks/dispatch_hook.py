"""DISPATCH hook: reads approved backlogs and dispatches Navigators.

Reads approved_backlogs from state_snapshot, dispatches each via
the DispatchOrchestrator. Idempotent: tracks processed ticks.
"""

from __future__ import annotations

from pathlib import Path

from computer.orchestration.orchestrator import DispatchOrchestrator
from engine.orchestration.models import Phase, PhaseResult, TickContext
from computer.planning.types import SprintBacklog, SprintTask


class DispatchHook:
    """Reads approved backlogs from state and dispatches Navigators."""

    def __init__(self, orchestrator: DispatchOrchestrator) -> None:
        self._orchestrator = orchestrator
        self._processed_ticks: set[int] = set()

    @property
    def phase(self) -> Phase:
        return Phase.DISPATCH

    @property
    def priority(self) -> int:
        return 10

    async def execute(self, context: TickContext) -> PhaseResult:
        if context.tick_number in self._processed_ticks:
            return PhaseResult(
                phase=Phase.DISPATCH, passed=True,
                findings=[], duration_ms=0.0,
            )
        self._processed_ticks.add(context.tick_number)

        backlogs = context.state_snapshot.get("approved_backlogs", [])
        if not backlogs:
            return PhaseResult(
                phase=Phase.DISPATCH, passed=True,
                findings=[], duration_ms=0.0,
            )

        findings: list[str] = []
        for bl_dict in backlogs:
            backlog = _backlog_from_dict(bl_dict)
            repo_path = Path(backlog.repo)
            result = self._orchestrator.dispatch(repo_path, backlog)
            findings.append(
                f"Dispatched {backlog.sprint_id} -> "
                f"{'success' if result.success else 'failed'}"
            )

        return PhaseResult(
            phase=Phase.DISPATCH, passed=True,
            findings=findings, duration_ms=0.0,
        )


def _backlog_from_dict(data: dict) -> SprintBacklog:
    """Reconstruct SprintBacklog from dict."""
    tasks = [
        SprintTask(
            task_id=t["task_id"], title=t["title"],
            description=t["description"],
            complexity=t["complexity"], priority=t["priority"],
            acceptance_criteria=t.get("acceptance_criteria", []),
            files=t.get("files", []), phase=t.get("phase", 1),
        )
        for t in data.get("tasks", [])
    ]
    return SprintBacklog(
        sprint_id=data["sprint_id"], repo=data["repo"],
        theme=data["theme"], goal=data["goal"],
        tasks=tasks, status=data.get("status", "approved"),
    )
