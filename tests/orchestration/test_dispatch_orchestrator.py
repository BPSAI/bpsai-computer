"""Tests for dispatch orchestrator and phase hooks.

Covers: CompletionStatus, ReviewResult, DispatchOrchestrator,
DispatchHook, ReviewHook, OutcomeHook.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from computer.orchestration.config import (
    CompletionStatus,
    DispatchResult,
    DispatchStatus,
    EnforcementMode,
)
from computer.orchestration.orchestrator import (
    DispatchOrchestrator,
    ReviewResult,
)
from engine.orchestration.models import Phase, PhaseResult, TickContext
from computer.planning.types import SprintBacklog, SprintTask


# ---------- helpers ----------


def _make_backlog(status: str = "approved") -> SprintBacklog:
    return SprintBacklog(
        sprint_id="S10",
        repo="bpsai-framework",
        theme="dispatch",
        goal="Ship dispatch orchestration",
        status=status,
        tasks=[
            SprintTask(
                task_id="T10.1", title="Task 1",
                description="First task", complexity=10, priority="P0",
            ),
        ],
    )


def _make_dispatch_result(
    success: bool = True,
    status: DispatchStatus = DispatchStatus.COMPLETE,
) -> DispatchResult:
    return DispatchResult(
        success=success, output="done", enforcement=EnforcementMode.CONTAINED_AUTO,
        method="subprocess", status=status, session_id="sess-1",
    )


def _make_tick_context(**snapshot_overrides) -> TickContext:
    snapshot = {"actions": [], "findings": []}
    snapshot.update(snapshot_overrides)
    return TickContext(
        tick_number=1, timestamp="2026-03-29T12:00:00Z",
        event_queue_snapshot=[], state_snapshot=snapshot,
    )


# ---------- CompletionStatus ----------


class TestCompletionStatus:
    def test_all_members_exist(self):
        assert CompletionStatus.PENDING.value == "pending"
        assert CompletionStatus.RUNNING.value == "running"
        assert CompletionStatus.PR_READY.value == "pr_ready"
        assert CompletionStatus.MERGED.value == "merged"
        assert CompletionStatus.FAILED.value == "failed"

    def test_is_terminal(self):
        assert CompletionStatus.MERGED.is_terminal
        assert CompletionStatus.FAILED.is_terminal
        assert not CompletionStatus.PENDING.is_terminal
        assert not CompletionStatus.RUNNING.is_terminal
        assert not CompletionStatus.PR_READY.is_terminal


# ---------- ReviewResult ----------


class TestReviewResult:
    def test_construction(self):
        r = ReviewResult(
            passed=True, findings=["looks good"],
            reviewer="reviewer", security_passed=True,
        )
        assert r.passed is True
        assert r.findings == ["looks good"]
        assert r.reviewer == "reviewer"
        assert r.security_passed is True

    def test_defaults(self):
        r = ReviewResult(passed=False, findings=["issue"])
        assert r.reviewer == ""
        assert r.security_passed is True

    def test_to_dict(self):
        r = ReviewResult(passed=True, findings=[], reviewer="rev")
        d = r.to_dict()
        assert d["passed"] is True
        assert d["reviewer"] == "rev"
        assert "findings" in d
        assert "security_passed" in d


# ---------- DispatchOrchestrator ----------


class TestDispatchOrchestratorPlanAndPropose:
    def test_returns_draft_backlog(self, tmp_path):
        planner = MagicMock()
        backlog = _make_backlog(status="draft")
        planner.plan.return_value = backlog
        orch = DispatchOrchestrator(planner=planner, dispatcher=MagicMock())
        result = orch.plan_and_propose(
            repo_path=tmp_path,
            standup_path=tmp_path / "standup.md",
            priorities_path=tmp_path / "priorities.md",
            sprint_id="S10", theme="dispatch",
        )
        assert result.status == "draft"
        planner.plan.assert_called_once()

    def test_always_returns_draft(self, tmp_path):
        planner = MagicMock()
        planner.plan.return_value = _make_backlog(status="approved")
        orch = DispatchOrchestrator(planner=planner, dispatcher=MagicMock())
        result = orch.plan_and_propose(
            repo_path=tmp_path,
            standup_path=tmp_path / "standup.md",
            priorities_path=tmp_path / "priorities.md",
            sprint_id="S10", theme="dispatch",
        )
        # plan_and_propose always forces draft status for human review
        assert result.status == "draft"


class TestDispatchOrchestratorDispatch:
    def test_rejects_non_approved_backlog(self, tmp_path):
        orch = DispatchOrchestrator(
            planner=MagicMock(), dispatcher=MagicMock(),
        )
        with pytest.raises(ValueError, match="approved"):
            orch.dispatch(tmp_path, _make_backlog(status="draft"))

    def test_dispatches_approved_backlog(self, tmp_path):
        dispatcher = MagicMock()
        dispatcher.dispatch_navigator.return_value = _make_dispatch_result()
        orch = DispatchOrchestrator(
            planner=MagicMock(), dispatcher=dispatcher,
        )
        result = orch.dispatch(tmp_path, _make_backlog(status="approved"))
        assert result.success is True
        dispatcher.dispatch_navigator.assert_called_once()

    def test_dispatch_config_has_enforcement(self, tmp_path):
        dispatcher = MagicMock()
        dispatcher.dispatch_navigator.return_value = _make_dispatch_result()
        orch = DispatchOrchestrator(
            planner=MagicMock(), dispatcher=dispatcher,
        )
        orch.dispatch(tmp_path, _make_backlog(status="approved"))
        config = dispatcher.dispatch_navigator.call_args[0][0]
        assert config.enforcement is not None


class TestDispatchOrchestratorMonitor:
    def test_complete_result_returns_pr_ready(self):
        orch = DispatchOrchestrator(
            planner=MagicMock(), dispatcher=MagicMock(),
        )
        result = _make_dispatch_result(
            success=True, status=DispatchStatus.COMPLETE,
        )
        assert orch.monitor(result) == CompletionStatus.PR_READY

    def test_failed_result_returns_failed(self):
        orch = DispatchOrchestrator(
            planner=MagicMock(), dispatcher=MagicMock(),
        )
        result = _make_dispatch_result(
            success=False, status=DispatchStatus.FAILED,
        )
        assert orch.monitor(result) == CompletionStatus.FAILED

    def test_running_result_returns_running(self):
        orch = DispatchOrchestrator(
            planner=MagicMock(), dispatcher=MagicMock(),
        )
        result = _make_dispatch_result(
            success=True, status=DispatchStatus.RUNNING,
        )
        assert orch.monitor(result) == CompletionStatus.RUNNING


class TestDispatchOrchestratorReview:
    def test_review_returns_review_result(self):
        orch = DispatchOrchestrator(
            planner=MagicMock(), dispatcher=MagicMock(),
        )
        result = _make_dispatch_result()
        review = orch.review(result)
        assert isinstance(review, ReviewResult)

    def test_review_of_failed_dispatch(self):
        orch = DispatchOrchestrator(
            planner=MagicMock(), dispatcher=MagicMock(),
        )
        result = _make_dispatch_result(success=False, status=DispatchStatus.FAILED)
        review = orch.review(result)
        assert review.passed is False
        assert any("failed" in f.lower() for f in review.findings)


# ---------- DispatchHook ----------


class TestDispatchHook:
    def test_phase_is_dispatch(self):
        from engine.orchestration.dispatch.dispatch_hook import DispatchHook
        hook = DispatchHook(orchestrator=MagicMock())
        assert hook.phase == Phase.DISPATCH

    def test_priority(self):
        from engine.orchestration.dispatch.dispatch_hook import DispatchHook
        hook = DispatchHook(orchestrator=MagicMock())
        assert isinstance(hook.priority, int)

    @pytest.mark.asyncio
    async def test_dispatches_approved_backlogs(self):
        from engine.orchestration.dispatch.dispatch_hook import DispatchHook
        orch = MagicMock()
        orch.dispatch.return_value = _make_dispatch_result()
        hook = DispatchHook(orchestrator=orch)
        backlog = _make_backlog(status="approved")
        ctx = _make_tick_context(approved_backlogs=[backlog.to_dict()])
        result = await hook.execute(ctx)
        assert result.passed is True
        orch.dispatch.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_when_no_backlogs(self):
        from engine.orchestration.dispatch.dispatch_hook import DispatchHook
        orch = MagicMock()
        hook = DispatchHook(orchestrator=orch)
        ctx = _make_tick_context()
        result = await hook.execute(ctx)
        assert result.passed is True
        orch.dispatch.assert_not_called()

    @pytest.mark.asyncio
    async def test_idempotent_across_ticks(self):
        from engine.orchestration.dispatch.dispatch_hook import DispatchHook
        orch = MagicMock()
        orch.dispatch.return_value = _make_dispatch_result()
        hook = DispatchHook(orchestrator=orch)
        backlog = _make_backlog(status="approved")
        ctx = _make_tick_context(approved_backlogs=[backlog.to_dict()])
        await hook.execute(ctx)
        await hook.execute(ctx)
        # Idempotent: same tick dispatched only once
        assert orch.dispatch.call_count == 1


# ---------- ReviewHook ----------


class TestReviewHook:
    def test_phase_is_enforce(self):
        from engine.orchestration.enforce.review_hook import ReviewHook
        hook = ReviewHook(orchestrator=MagicMock())
        assert hook.phase == Phase.ENFORCE

    @pytest.mark.asyncio
    async def test_reviews_completed_dispatches(self):
        from engine.orchestration.enforce.review_hook import ReviewHook
        orch = MagicMock()
        orch.review.return_value = ReviewResult(
            passed=True, findings=["ok"],
        )
        hook = ReviewHook(orchestrator=orch)
        dispatch_result = _make_dispatch_result()
        ctx = _make_tick_context(
            completed_dispatches=[{
                "success": True, "output": "done",
                "enforcement": "contained-auto", "method": "subprocess",
                "status": "complete", "session_id": "sess-1",
            }],
        )
        result = await hook.execute(ctx)
        assert result.passed is True
        orch.review.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_when_no_completed_dispatches(self):
        from engine.orchestration.enforce.review_hook import ReviewHook
        orch = MagicMock()
        hook = ReviewHook(orchestrator=orch)
        ctx = _make_tick_context()
        result = await hook.execute(ctx)
        assert result.passed is True
        orch.review.assert_not_called()

    @pytest.mark.asyncio
    async def test_idempotent(self):
        from engine.orchestration.enforce.review_hook import ReviewHook
        orch = MagicMock()
        orch.review.return_value = ReviewResult(passed=True, findings=[])
        hook = ReviewHook(orchestrator=orch)
        ctx = _make_tick_context(
            completed_dispatches=[{
                "success": True, "output": "done",
                "enforcement": "contained-auto", "method": "subprocess",
                "status": "complete", "session_id": "sess-1",
            }],
        )
        await hook.execute(ctx)
        await hook.execute(ctx)
        assert orch.review.call_count == 1


# ---------- PhaseRegistry integration ----------


class TestHookRegistration:
    def test_dispatch_and_review_hooks_satisfy_protocol(self):
        from engine.orchestration.dispatch.dispatch_hook import DispatchHook
        from engine.orchestration.enforce.review_hook import ReviewHook
        from engine.orchestration.phase_registry import PhaseHook, PhaseRegistry

        registry = PhaseRegistry()
        hooks = [
            DispatchHook(orchestrator=MagicMock()),
            ReviewHook(orchestrator=MagicMock()),
        ]
        for hook in hooks:
            assert isinstance(hook, PhaseHook)
            registry.register(hook)
        assert registry.count() == 2
