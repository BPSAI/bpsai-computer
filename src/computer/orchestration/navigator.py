"""Navigator Dispatch Orchestration — Computer DISPATCH phase.

Wires the sprint planner, backlog deliverer, and dispatcher into a
single orchestrated flow: approve -> deliver -> dispatch -> monitor ->
review -> complete. All outcomes recorded in the Decision Journal.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from computer.planning.deliver import BacklogDeliverer, DeliveryResult
from computer.status.completion import CompletionDetector, CompletionStatus
from engine.decision_journal import CNSDecision, DecisionJournal, DecisionType
from computer.orchestration import DispatchResult, Dispatcher
from computer.review.automation import ReviewDispatcher, ReviewResult
from computer.planning.types import SprintBacklog


class OrchestrationPhase(Enum):
    PLAN = "plan"
    APPROVE = "approve"
    DELIVER = "deliver"
    DISPATCH = "dispatch"
    MONITOR = "monitor"
    REVIEW = "review"
    COMPLETE = "complete"


@dataclass
class OrchestrationOutcome:
    """Result of a full orchestration run."""

    success: bool
    phase_reached: OrchestrationPhase
    error: str = ""
    delivery_result: Optional[DeliveryResult] = None
    dispatch_result: Optional[DispatchResult] = None
    review_dispatched: bool = False
    review_result: Optional[ReviewResult] = None
    decision_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "phase_reached": self.phase_reached.value,
            "error": self.error,
            "review_dispatched": self.review_dispatched,
            "review_result": self.review_result.to_dict() if self.review_result else None,
            "decision_id": self.decision_id,
        }


class NavigatorOrchestrator:
    """Orchestrates the full Computer DISPATCH phase.

    Flow: approve -> deliver -> dispatch -> monitor -> review -> journal.
    """

    def __init__(
        self, dispatcher: Dispatcher, deliverer: BacklogDeliverer,
        detector: CompletionDetector, journal: DecisionJournal,
        review_dispatcher: Optional[ReviewDispatcher] = None,
    ) -> None:
        self._dispatcher = dispatcher
        self._deliverer = deliverer
        self._detector = detector
        self._journal = journal
        self._review_dispatcher = review_dispatcher or ReviewDispatcher(dispatcher)

    def run(
        self, backlog: SprintBacklog, repo_path: Path, backlog_dir: Path,
        channel_data: Optional[dict[str, Any]] = None,
    ) -> OrchestrationOutcome:
        """Execute the full orchestration flow."""
        repo_path = Path(repo_path)
        backlog_dir = Path(backlog_dir)

        if backlog.status != "approved":
            return OrchestrationOutcome(
                success=False, phase_reached=OrchestrationPhase.APPROVE,
                error=f"Backlog must be approved (status: {backlog.status})",
            )

        filename = f"{backlog.repo}-sprint-{backlog.sprint_id}.md"
        delivery = self._deliverer.deliver(
            backlog=backlog, target_dir=backlog_dir,
            filename=filename, overwrite=True,
        )
        if not delivery.success:
            return OrchestrationOutcome(
                success=False, phase_reached=OrchestrationPhase.DELIVER,
                error=delivery.error, delivery_result=delivery,
            )

        prompt = _build_prompt(backlog, delivery.path)
        dispatch_result = self._dispatcher.dispatch(repo_path, prompt)

        if not dispatch_result.success:
            self._record(backlog, dispatch_result, success=False)
            return OrchestrationOutcome(
                success=False, phase_reached=OrchestrationPhase.DISPATCH,
                error=f"Dispatch failed: {dispatch_result.output}",
                delivery_result=delivery, dispatch_result=dispatch_result,
            )

        completion = _check_completion(
            self._detector, repo_path, backlog.sprint_id, channel_data,
        )
        if completion == CompletionStatus.ERROR:
            self._record(backlog, dispatch_result, success=False)
            return OrchestrationOutcome(
                success=False, phase_reached=OrchestrationPhase.MONITOR,
                error="Navigator reported error",
                delivery_result=delivery, dispatch_result=dispatch_result,
            )

        _TERMINAL_OK = {CompletionStatus.COMPLETE, CompletionStatus.PR_READY}
        if completion not in _TERMINAL_OK:
            self._record(backlog, dispatch_result, success=False)
            return OrchestrationOutcome(
                success=False, phase_reached=OrchestrationPhase.MONITOR,
                error=f"Navigator not yet complete (status: {completion.value})",
                delivery_result=delivery, dispatch_result=dispatch_result,
            )

        review_result = self._dispatch_review(repo_path, backlog)
        review_ok = review_result.reviewer_dispatched or review_result.auditor_dispatched
        decision_id = self._record(backlog, dispatch_result, success=True)

        return OrchestrationOutcome(
            success=True, phase_reached=OrchestrationPhase.COMPLETE,
            delivery_result=delivery, dispatch_result=dispatch_result,
            review_dispatched=review_ok, review_result=review_result,
            decision_id=decision_id,
        )

    def _dispatch_review(
        self, repo_path: Path, backlog: SprintBacklog,
    ) -> ReviewResult:
        try:
            return self._review_dispatcher.review(repo_path, backlog)
        except Exception:
            return ReviewResult()

    def _record(
        self, backlog: SprintBacklog, result: DispatchResult, success: bool,
    ) -> str:
        decision = CNSDecision(
            decision_id="", timestamp="",
            decision_type=DecisionType.DISPATCH,
            observation=f"Sprint {backlog.sprint_id} ({backlog.theme}) dispatched to {backlog.repo}",
            diagnosis=f"{len(backlog.tasks)} tasks, {backlog.total_complexity}cx",
            prescription=f"Dispatched via {result.method} with {result.enforcement.value}",
            expected_outcome=f"Sprint {backlog.sprint_id} completed",
            actual_outcome="Completed" if success else f"Failed: {result.output[:200]}",
            effectiveness="effective" if success else "ineffective",
        )
        recorded = self._journal.record(decision)
        return recorded.decision_id


def _build_prompt(backlog: SprintBacklog, backlog_path: Path) -> str:
    task_list = ", ".join(t.task_id for t in backlog.tasks)
    return (
        f"Execute sprint {backlog.sprint_id} ({backlog.theme}) "
        f"for repo {backlog.repo}. Backlog at {backlog_path}. "
        f"Tasks: {task_list}. Goal: {backlog.goal}"
    )


def _check_completion(
    detector: CompletionDetector, repo_path: Path,
    sprint_id: str, channel_data: Optional[dict[str, Any]],
) -> CompletionStatus:
    if channel_data is not None:
        return detector.check_channel(channel_data)
    return detector.check_git(repo_path, branch=f"sprint/{sprint_id}")
