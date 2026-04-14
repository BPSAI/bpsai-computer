"""Dispatch orchestrator — connects sprint planner with dispatcher.

Implements the PLAN -> DISPATCH -> ENFORCE -> LEARN loop:
- plan_and_propose: run planner, return draft for human review
- dispatch: deliver approved backlog + launch Navigator with enforcement
- monitor: poll for completion status
- review: dispatch reviewer against completed work
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from computer.orchestration.config import (
    CompletionStatus,
    DispatchConfig,
    DispatchResult,
    DispatchStatus,
    EnforcementMode,
)
from computer.orchestration.dispatcher import Dispatcher
from computer.planning.planner import SprintPlanner
from computer.planning.types import SprintBacklog


@dataclass
class ReviewResult:
    """Outcome of reviewing a completed dispatch."""

    passed: bool
    findings: list[str]
    reviewer: str = ""
    security_passed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "findings": list(self.findings),
            "reviewer": self.reviewer,
            "security_passed": self.security_passed,
        }


class DispatchOrchestrator:
    """Connects sprint planner with dispatcher for full loop."""

    def __init__(
        self, planner: SprintPlanner, dispatcher: Dispatcher,
    ) -> None:
        self._planner = planner
        self._dispatcher = dispatcher

    def plan_and_propose(
        self, repo_path: Path, standup_path: Path,
        priorities_path: Path, sprint_id: str, theme: str,
        goal: str = "",
    ) -> SprintBacklog:
        """Run planner and return draft backlog for human review."""
        backlog = self._planner.plan(
            standup_path=standup_path,
            priorities_path=priorities_path,
            target_repo=str(repo_path),
            sprint_id=sprint_id,
            theme=theme,
            goal=goal,
        )
        backlog.status = "draft"
        return backlog

    def dispatch(
        self, repo_path: Path, backlog: SprintBacklog,
    ) -> DispatchResult:
        """Dispatch an approved backlog to a Navigator session."""
        if backlog.status != "approved":
            raise ValueError(
                f"Backlog must be approved before dispatch, "
                f"got status={backlog.status!r}"
            )
        prompt = _build_dispatch_prompt(backlog)
        config = DispatchConfig(
            repo_path=Path(repo_path),
            prompt=prompt,
            enforcement=EnforcementMode.CONTAINED_AUTO,
        )
        return self._dispatcher.dispatch_navigator(config)

    def monitor(self, result: DispatchResult) -> CompletionStatus:
        """Map dispatch result to completion status."""
        if result.status == DispatchStatus.FAILED or not result.success:
            return CompletionStatus.FAILED
        if result.status == DispatchStatus.RUNNING:
            return CompletionStatus.RUNNING
        if result.status == DispatchStatus.COMPLETE:
            return CompletionStatus.PR_READY
        return CompletionStatus.PENDING

    def review(self, result: DispatchResult) -> ReviewResult:
        """Produce a review result for a completed dispatch."""
        if not result.success:
            return ReviewResult(
                passed=False,
                findings=[f"Dispatch failed: {result.output[:200]}"],
                reviewer="dispatch-orchestrator",
            )
        return ReviewResult(
            passed=True,
            findings=["Dispatch completed successfully"],
            reviewer="dispatch-orchestrator",
        )


def _build_dispatch_prompt(backlog: SprintBacklog) -> str:
    """Build prompt for Navigator from backlog."""
    task_lines = "\n".join(
        f"- {t.task_id}: {t.title} (Cx:{t.complexity}, {t.priority})"
        for t in backlog.tasks
    )
    return (
        f"Sprint {backlog.sprint_id}: {backlog.theme}\n"
        f"Goal: {backlog.goal}\n\nTasks:\n{task_lines}"
    )
