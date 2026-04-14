"""Tests for Navigator Dispatch Orchestration — Computer₀ DISPATCH phase.

Covers: full dispatch flow (plan → approve → deliver → dispatch → monitor → review),
RC/subprocess dispatch modes, completion detection (channel + git polling),
review agent dispatch, and Decision Journal recording.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from computer.planning.deliver import BacklogDeliverer, DeliveryResult
from engine.decision_journal import CNSDecision, DecisionJournal, DecisionType
from computer.orchestration import DispatchResult, Dispatcher, EnforcementMode
from computer.orchestration.navigator import (
    CompletionDetector,
    CompletionStatus,
    NavigatorOrchestrator,
    OrchestrationOutcome,
    OrchestrationPhase,
)
from engine.sprint_planner import SprintBacklog, SprintTask


# ---------- Helpers ----------


def _sample_backlog() -> SprintBacklog:
    return SprintBacklog(
        sprint_id="Bot-S35",
        repo="paircoder_bot",
        theme="Test Sprint",
        goal="Test goal",
        tasks=[
            SprintTask("T35.1", "Task A", "Desc A", 10, "P0"),
            SprintTask("T35.2", "Task B", "Desc B", 15, "P1"),
        ],
        status="approved",
    )


def _mock_dispatch_success() -> DispatchResult:
    return DispatchResult(
        success=True,
        output="Navigator completed",
        enforcement=EnforcementMode.CONTAINED_AUTO,
        method="subprocess",
    )


def _mock_dispatch_rc_success() -> DispatchResult:
    return DispatchResult(
        success=True,
        output="Navigator completed via RC",
        enforcement=EnforcementMode.CONTAINED_AUTO,
        method="rc",
    )


# ---------- OrchestrationPhase ----------


class TestOrchestrationPhase:
    def test_phase_ordering(self):
        phases = list(OrchestrationPhase)
        names = [p.name for p in phases]
        assert names.index("PLAN") < names.index("APPROVE")
        assert names.index("APPROVE") < names.index("DELIVER")
        assert names.index("DELIVER") < names.index("DISPATCH")
        assert names.index("DISPATCH") < names.index("MONITOR")
        assert names.index("MONITOR") < names.index("REVIEW")
        assert names.index("REVIEW") < names.index("COMPLETE")


# ---------- CompletionDetector ----------


class TestCompletionDetector:
    def test_git_polling_detects_new_commits(self, tmp_path):
        """Git polling detects completion via new commits on branch."""
        detector = CompletionDetector()
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        # No git repo = not complete
        status = detector.check_git(repo_path, branch="sprint/Bot-S35")
        assert status == CompletionStatus.IN_PROGRESS

    def test_git_polling_detects_pr(self, tmp_path):
        """Git polling detects completion when PR exists."""
        detector = CompletionDetector()
        # Mock gh pr list returning a PR
        with patch("engine.completion_detector.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='[{"number": 5, "state": "OPEN"}]',
            )
            status = detector.check_git(
                tmp_path, branch="sprint/Bot-S35",
            )
            assert status == CompletionStatus.PR_READY

    def test_git_polling_no_pr(self, tmp_path):
        """No PR means still in progress."""
        detector = CompletionDetector()
        with patch("engine.completion_detector.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="[]",
            )
            status = detector.check_git(
                tmp_path, branch="sprint/Bot-S35",
            )
            assert status == CompletionStatus.IN_PROGRESS

    def test_channel_monitoring_detects_completion(self):
        """Channel monitoring detects completion signal."""
        detector = CompletionDetector()
        channel_data = {
            "type": "sprint_complete",
            "sprint_id": "Bot-S35",
            "status": "done",
        }
        status = detector.check_channel(channel_data)
        assert status == CompletionStatus.COMPLETE

    def test_channel_monitoring_in_progress(self):
        """Channel with no completion signal = in progress."""
        detector = CompletionDetector()
        channel_data = {
            "type": "progress_update",
            "sprint_id": "Bot-S35",
            "tasks_done": 3,
        }
        status = detector.check_channel(channel_data)
        assert status == CompletionStatus.IN_PROGRESS

    def test_channel_monitoring_with_error(self):
        """Channel reports error status."""
        detector = CompletionDetector()
        channel_data = {
            "type": "sprint_error",
            "sprint_id": "Bot-S35",
            "error": "dispatch failed",
        }
        status = detector.check_channel(channel_data)
        assert status == CompletionStatus.ERROR


# ---------- NavigatorOrchestrator ----------


class TestNavigatorOrchestrator:
    def _make_orchestrator(self, tmp_path):
        journal_path = tmp_path / "decisions.jsonl"
        journal = DecisionJournal(journal_path)
        dispatcher = MagicMock(spec=Dispatcher)
        deliverer = MagicMock(spec=BacklogDeliverer)
        detector = MagicMock(spec=CompletionDetector)

        orch = NavigatorOrchestrator(
            dispatcher=dispatcher,
            deliverer=deliverer,
            detector=detector,
            journal=journal,
        )
        return orch, dispatcher, deliverer, detector, journal

    def test_full_flow_plan_to_complete(self, tmp_path):
        """Full flow: deliver → dispatch → monitor → review → journal."""
        orch, dispatcher, deliverer, detector, journal = (
            self._make_orchestrator(tmp_path)
        )

        repo_path = tmp_path / "target_repo"
        repo_path.mkdir()
        backlog_dir = repo_path / "plans" / "backlogs"
        backlog_dir.mkdir(parents=True)

        # Mock deliverer
        deliverer.deliver.return_value = DeliveryResult(
            success=True,
            path=backlog_dir / "bot-sprint-35.md",
        )

        # Mock dispatcher — navigator dispatch + review dispatch
        dispatcher.dispatch.return_value = _mock_dispatch_success()

        # Mock detector — complete on first check
        detector.check_git.return_value = CompletionStatus.PR_READY

        backlog = _sample_backlog()
        outcome = orch.run(
            backlog=backlog,
            repo_path=repo_path,
            backlog_dir=backlog_dir,
        )

        assert isinstance(outcome, OrchestrationOutcome)
        assert outcome.success is True
        assert outcome.phase_reached == OrchestrationPhase.COMPLETE
        assert outcome.dispatch_result is not None
        assert outcome.review_dispatched is True

        # Decision recorded in journal
        decisions = journal.list_by_type(DecisionType.DISPATCH)
        assert len(decisions) >= 1
        assert decisions[0].observation != ""

    def test_delivery_failure_stops_flow(self, tmp_path):
        """If delivery fails, flow stops before dispatch."""
        orch, dispatcher, deliverer, detector, journal = (
            self._make_orchestrator(tmp_path)
        )

        repo_path = tmp_path / "target_repo"
        repo_path.mkdir()

        deliverer.deliver.return_value = DeliveryResult(
            success=False,
            path=repo_path / "backlogs" / "test.md",
            error="Target directory does not exist",
        )

        outcome = orch.run(
            backlog=_sample_backlog(),
            repo_path=repo_path,
            backlog_dir=repo_path / "backlogs",
        )

        assert outcome.success is False
        assert outcome.phase_reached == OrchestrationPhase.DELIVER
        assert outcome.error != ""
        dispatcher.dispatch.assert_not_called()

    def test_dispatch_failure_stops_flow(self, tmp_path):
        """If dispatch fails, flow stops before monitor."""
        orch, dispatcher, deliverer, detector, journal = (
            self._make_orchestrator(tmp_path)
        )

        repo_path = tmp_path / "target_repo"
        repo_path.mkdir()
        backlog_dir = repo_path / "plans" / "backlogs"
        backlog_dir.mkdir(parents=True)

        deliverer.deliver.return_value = DeliveryResult(
            success=True,
            path=backlog_dir / "test.md",
        )

        dispatcher.dispatch.return_value = DispatchResult(
            success=False,
            output="Claude not found",
            enforcement=EnforcementMode.CONTAINED_AUTO,
            method="subprocess",
        )

        outcome = orch.run(
            backlog=_sample_backlog(),
            repo_path=repo_path,
            backlog_dir=backlog_dir,
        )

        assert outcome.success is False
        assert outcome.phase_reached == OrchestrationPhase.DISPATCH
        detector.check_git.assert_not_called()

    def test_works_with_rc_mode(self, tmp_path):
        """Dispatch uses RC mode when available."""
        orch, dispatcher, deliverer, detector, journal = (
            self._make_orchestrator(tmp_path)
        )

        repo_path = tmp_path / "target_repo"
        repo_path.mkdir()
        backlog_dir = repo_path / "plans" / "backlogs"
        backlog_dir.mkdir(parents=True)

        deliverer.deliver.return_value = DeliveryResult(
            success=True, path=backlog_dir / "test.md",
        )

        # RC mode dispatch
        dispatcher.dispatch.return_value = _mock_dispatch_rc_success()
        detector.check_git.return_value = CompletionStatus.PR_READY

        outcome = orch.run(
            backlog=_sample_backlog(),
            repo_path=repo_path,
            backlog_dir=backlog_dir,
        )

        assert outcome.success is True
        assert outcome.dispatch_result.method == "rc"

    def test_works_with_subprocess_fallback(self, tmp_path):
        """Dispatch falls back to subprocess when RC unavailable."""
        orch, dispatcher, deliverer, detector, journal = (
            self._make_orchestrator(tmp_path)
        )

        repo_path = tmp_path / "target_repo"
        repo_path.mkdir()
        backlog_dir = repo_path / "plans" / "backlogs"
        backlog_dir.mkdir(parents=True)

        deliverer.deliver.return_value = DeliveryResult(
            success=True, path=backlog_dir / "test.md",
        )

        dispatcher.dispatch.return_value = _mock_dispatch_success()
        detector.check_git.return_value = CompletionStatus.PR_READY

        outcome = orch.run(
            backlog=_sample_backlog(),
            repo_path=repo_path,
            backlog_dir=backlog_dir,
        )

        assert outcome.success is True
        assert outcome.dispatch_result.method == "subprocess"

    def test_channel_monitoring_when_available(self, tmp_path):
        """Uses channel monitoring when channel data provided."""
        orch, dispatcher, deliverer, detector, journal = (
            self._make_orchestrator(tmp_path)
        )

        repo_path = tmp_path / "target_repo"
        repo_path.mkdir()
        backlog_dir = repo_path / "plans" / "backlogs"
        backlog_dir.mkdir(parents=True)

        deliverer.deliver.return_value = DeliveryResult(
            success=True, path=backlog_dir / "test.md",
        )
        dispatcher.dispatch.return_value = _mock_dispatch_success()
        detector.check_channel.return_value = CompletionStatus.COMPLETE

        channel_data = {
            "type": "sprint_complete",
            "sprint_id": "Bot-S35",
            "status": "done",
        }
        outcome = orch.run(
            backlog=_sample_backlog(),
            repo_path=repo_path,
            backlog_dir=backlog_dir,
            channel_data=channel_data,
        )

        assert outcome.success is True
        detector.check_channel.assert_called_once_with(channel_data)
        detector.check_git.assert_not_called()

    def test_git_polling_fallback_when_no_channel(self, tmp_path):
        """Falls back to git polling when no channel data."""
        orch, dispatcher, deliverer, detector, journal = (
            self._make_orchestrator(tmp_path)
        )

        repo_path = tmp_path / "target_repo"
        repo_path.mkdir()
        backlog_dir = repo_path / "plans" / "backlogs"
        backlog_dir.mkdir(parents=True)

        deliverer.deliver.return_value = DeliveryResult(
            success=True, path=backlog_dir / "test.md",
        )
        dispatcher.dispatch.return_value = _mock_dispatch_success()
        detector.check_git.return_value = CompletionStatus.PR_READY

        outcome = orch.run(
            backlog=_sample_backlog(),
            repo_path=repo_path,
            backlog_dir=backlog_dir,
            # No channel_data — falls back to git
        )

        assert outcome.success is True
        detector.check_git.assert_called_once()

    def test_review_agents_dispatched_on_completion(self, tmp_path):
        """Review agents dispatched after navigator completes."""
        orch, dispatcher, deliverer, detector, journal = (
            self._make_orchestrator(tmp_path)
        )

        repo_path = tmp_path / "target_repo"
        repo_path.mkdir()
        backlog_dir = repo_path / "plans" / "backlogs"
        backlog_dir.mkdir(parents=True)

        deliverer.deliver.return_value = DeliveryResult(
            success=True, path=backlog_dir / "test.md",
        )
        dispatcher.dispatch.return_value = _mock_dispatch_success()
        detector.check_git.return_value = CompletionStatus.PR_READY

        outcome = orch.run(
            backlog=_sample_backlog(),
            repo_path=repo_path,
            backlog_dir=backlog_dir,
        )

        assert outcome.review_dispatched is True
        # Dispatcher called 3 times: navigator + reviewer + security-auditor
        assert dispatcher.dispatch.call_count == 3
        review_calls = dispatcher.dispatch.call_args_list[1:]
        prompts = [str(c).lower() for c in review_calls]
        assert any("review" in p for p in prompts)
        assert any("security" in p for p in prompts)

    def test_outcomes_recorded_in_decision_journal(self, tmp_path):
        """Decision journal records dispatch outcome."""
        orch, dispatcher, deliverer, detector, journal = (
            self._make_orchestrator(tmp_path)
        )

        repo_path = tmp_path / "target_repo"
        repo_path.mkdir()
        backlog_dir = repo_path / "plans" / "backlogs"
        backlog_dir.mkdir(parents=True)

        deliverer.deliver.return_value = DeliveryResult(
            success=True, path=backlog_dir / "test.md",
        )
        dispatcher.dispatch.return_value = _mock_dispatch_success()
        detector.check_git.return_value = CompletionStatus.PR_READY

        orch.run(
            backlog=_sample_backlog(),
            repo_path=repo_path,
            backlog_dir=backlog_dir,
        )

        decisions = journal.list_by_type(DecisionType.DISPATCH)
        assert len(decisions) == 1
        dec = decisions[0]
        assert "Bot-S35" in dec.observation
        assert dec.actual_outcome is not None
        assert dec.effectiveness == "effective"

    def test_failed_dispatch_recorded_as_ineffective(self, tmp_path):
        """Failed dispatch recorded with ineffective effectiveness."""
        orch, dispatcher, deliverer, detector, journal = (
            self._make_orchestrator(tmp_path)
        )

        repo_path = tmp_path / "target_repo"
        repo_path.mkdir()
        backlog_dir = repo_path / "plans" / "backlogs"
        backlog_dir.mkdir(parents=True)

        deliverer.deliver.return_value = DeliveryResult(
            success=True, path=backlog_dir / "test.md",
        )
        dispatcher.dispatch.return_value = DispatchResult(
            success=False,
            output="Failed",
            enforcement=EnforcementMode.CONTAINED_AUTO,
            method="subprocess",
        )

        orch.run(
            backlog=_sample_backlog(),
            repo_path=repo_path,
            backlog_dir=backlog_dir,
        )

        decisions = journal.list_by_type(DecisionType.DISPATCH)
        assert len(decisions) == 1
        assert decisions[0].effectiveness == "ineffective"

    def test_backlog_must_be_approved(self, tmp_path):
        """Orchestrator rejects backlogs that are not approved."""
        orch, dispatcher, deliverer, detector, journal = (
            self._make_orchestrator(tmp_path)
        )

        repo_path = tmp_path / "target_repo"
        repo_path.mkdir()
        backlog_dir = repo_path / "plans" / "backlogs"
        backlog_dir.mkdir(parents=True)

        draft_backlog = _sample_backlog()
        draft_backlog.status = "draft"

        outcome = orch.run(
            backlog=draft_backlog,
            repo_path=repo_path,
            backlog_dir=backlog_dir,
        )

        assert outcome.success is False
        assert outcome.phase_reached == OrchestrationPhase.APPROVE
        assert "approved" in outcome.error.lower()
        dispatcher.dispatch.assert_not_called()

    def test_monitor_error_stops_before_review(self, tmp_path):
        """Monitor error prevents review dispatch."""
        orch, dispatcher, deliverer, detector, journal = (
            self._make_orchestrator(tmp_path)
        )

        repo_path = tmp_path / "target_repo"
        repo_path.mkdir()
        backlog_dir = repo_path / "plans" / "backlogs"
        backlog_dir.mkdir(parents=True)

        deliverer.deliver.return_value = DeliveryResult(
            success=True, path=backlog_dir / "test.md",
        )
        dispatcher.dispatch.return_value = _mock_dispatch_success()
        detector.check_git.return_value = CompletionStatus.ERROR

        outcome = orch.run(
            backlog=_sample_backlog(),
            repo_path=repo_path,
            backlog_dir=backlog_dir,
        )

        assert outcome.success is False
        assert outcome.phase_reached == OrchestrationPhase.MONITOR
        assert outcome.review_dispatched is False
        # Only navigator dispatch, no review
        assert dispatcher.dispatch.call_count == 1
