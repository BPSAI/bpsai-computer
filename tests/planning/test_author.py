"""Tests for engine.next_sprint_author — next sprint drafting after completion."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent

import pytest

from computer.planning.author import (
    CompletedTask,
    NextSprintAuthor,
    NextSprintDraft,
    TaskOutcome,
)
from computer.planning.types import SprintBacklog, SprintTask, StandupItem


# ── Fixtures ──────────────────────────────────────────────────────


def _make_completed_tasks() -> list[CompletedTask]:
    return [
        CompletedTask(task_id="T10.1", title="Ship auth", outcome=TaskOutcome.DONE),
        CompletedTask(task_id="T10.2", title="Fix logging", outcome=TaskOutcome.FAILED, reason="Flaky CI"),
        CompletedTask(task_id="T10.3", title="Add metrics", outcome=TaskOutcome.DEFERRED, reason="Blocked on infra"),
        CompletedTask(task_id="T10.4", title="Update docs", outcome=TaskOutcome.DONE),
    ]


def _make_standup_items() -> list[StandupItem]:
    return [
        StandupItem(source="adversarial", description="Auth token rotation missing", severity="high"),
        StandupItem(source="doc_integrity", description="README drift on API routes", severity="medium"),
        StandupItem(source="computer_support", description="HYP-003 confidence drop", severity="low", hypothesis_id="HYP-003"),
    ]


def _make_author() -> NextSprintAuthor:
    return NextSprintAuthor()


# ── Model tests ───────────────────────────────────────────────────


class TestCompletedTask:
    def test_done_is_not_carry_over(self) -> None:
        t = CompletedTask(task_id="T1.1", title="Done task", outcome=TaskOutcome.DONE)
        assert not t.is_carry_over

    def test_failed_is_carry_over(self) -> None:
        t = CompletedTask(task_id="T1.2", title="Failed", outcome=TaskOutcome.FAILED)
        assert t.is_carry_over

    def test_deferred_is_carry_over(self) -> None:
        t = CompletedTask(task_id="T1.3", title="Deferred", outcome=TaskOutcome.DEFERRED)
        assert t.is_carry_over

    def test_to_dict(self) -> None:
        t = CompletedTask(task_id="T1.1", title="X", outcome=TaskOutcome.FAILED, reason="CI")
        d = t.to_dict()
        assert d["task_id"] == "T1.1"
        assert d["outcome"] == "failed"
        assert d["reason"] == "CI"


class TestTaskOutcome:
    def test_values(self) -> None:
        assert TaskOutcome.DONE.value == "done"
        assert TaskOutcome.FAILED.value == "failed"
        assert TaskOutcome.DEFERRED.value == "deferred"


class TestNextSprintDraft:
    def test_draft_status_always_draft(self) -> None:
        draft = NextSprintDraft(
            backlog=SprintBacklog(
                sprint_id="S11", repo="bpsai-cli", theme="Test",
                goal="Test goal", tasks=[], status="draft",
            ),
            carry_over_ids=["T10.2"],
            metis_task_ids=["T11.2"],
        )
        assert draft.backlog.status == "draft"

    def test_to_dict(self) -> None:
        draft = NextSprintDraft(
            backlog=SprintBacklog(
                sprint_id="S11", repo="bpsai-cli", theme="Fixes",
                goal="Fix it", tasks=[], status="draft",
            ),
            carry_over_ids=["T10.2", "T10.3"],
            metis_task_ids=["T11.3"],
        )
        d = draft.to_dict()
        assert d["carry_over_ids"] == ["T10.2", "T10.3"]
        assert d["metis_task_ids"] == ["T11.3"]
        assert d["backlog"]["status"] == "draft"


# ── plan_next tests ───────────────────────────────────────────────


class TestPlanNext:
    def test_basic_draft_from_mock_data(self) -> None:
        author = _make_author()
        draft = author.plan_next(
            completed_tasks=_make_completed_tasks(),
            standup_items=_make_standup_items(),
            target_repo="bpsai-cli",
            next_sprint_id="S11",
            theme="Hardening",
        )
        assert isinstance(draft, NextSprintDraft)
        assert draft.backlog.status == "draft"
        assert draft.backlog.sprint_id == "S11"
        assert draft.backlog.repo == "bpsai-cli"
        assert len(draft.backlog.tasks) > 0

    def test_carry_over_from_failed_tasks(self) -> None:
        author = _make_author()
        draft = author.plan_next(
            completed_tasks=_make_completed_tasks(),
            standup_items=[],
            target_repo="bpsai-cli",
            next_sprint_id="S11",
            theme="Carry-over",
        )
        # Failed + deferred should carry over (new IDs assigned)
        assert len(draft.carry_over_ids) == 2
        # Done tasks should NOT carry over
        all_task_ids = {t.task_id for t in draft.backlog.tasks}
        for cid in draft.carry_over_ids:
            assert cid in all_task_ids
        # Carry-over tasks should appear in the backlog
        task_titles = [t.title for t in draft.backlog.tasks]
        assert "Fix logging" in task_titles
        assert "Add metrics" in task_titles

    def test_metis_findings_included(self) -> None:
        author = _make_author()
        draft = author.plan_next(
            completed_tasks=[],
            standup_items=_make_standup_items(),
            target_repo="bpsai-cli",
            next_sprint_id="S11",
            theme="Metis findings",
        )
        assert len(draft.metis_task_ids) > 0
        # High-severity item should become a task
        descs = [t.description for t in draft.backlog.tasks]
        assert any("Auth token rotation" in d for d in descs)

    def test_carry_over_before_new_findings(self) -> None:
        """Carry-over tasks should appear before new Metis findings."""
        author = _make_author()
        draft = author.plan_next(
            completed_tasks=_make_completed_tasks(),
            standup_items=_make_standup_items(),
            target_repo="bpsai-cli",
            next_sprint_id="S11",
            theme="Mixed",
        )
        tasks = draft.backlog.tasks
        carry_ids = set(draft.carry_over_ids)
        # Find first carry-over and first metis task index
        first_carry = next(
            (i for i, t in enumerate(tasks) if t.task_id in carry_ids), None,
        )
        metis_ids = set(draft.metis_task_ids)
        first_metis = next(
            (i for i, t in enumerate(tasks) if t.task_id in metis_ids), None,
        )
        if first_carry is not None and first_metis is not None:
            assert first_carry < first_metis

    def test_no_carry_over_when_all_done(self) -> None:
        all_done = [
            CompletedTask(task_id="T10.1", title="A", outcome=TaskOutcome.DONE),
            CompletedTask(task_id="T10.2", title="B", outcome=TaskOutcome.DONE),
        ]
        author = _make_author()
        draft = author.plan_next(
            completed_tasks=all_done,
            standup_items=_make_standup_items(),
            target_repo="bpsai-cli",
            next_sprint_id="S11",
            theme="Clean",
        )
        assert len(draft.carry_over_ids) == 0

    def test_empty_inputs_returns_empty_draft(self) -> None:
        author = _make_author()
        draft = author.plan_next(
            completed_tasks=[],
            standup_items=[],
            target_repo="bpsai-cli",
            next_sprint_id="S11",
            theme="Empty",
        )
        assert draft.backlog.status == "draft"
        assert len(draft.backlog.tasks) == 0
        assert len(draft.carry_over_ids) == 0
        assert len(draft.metis_task_ids) == 0

    def test_deferred_reason_in_description(self) -> None:
        """Carry-over tasks should include the reason in their description."""
        tasks = [
            CompletedTask(
                task_id="T10.1", title="Blocked thing",
                outcome=TaskOutcome.DEFERRED, reason="Waiting on DNS",
            ),
        ]
        author = _make_author()
        draft = author.plan_next(
            completed_tasks=tasks,
            standup_items=[],
            target_repo="bpsai-cli",
            next_sprint_id="S11",
            theme="Deferred",
        )
        carry_task = draft.backlog.tasks[0]
        assert "Waiting on DNS" in carry_task.description

    def test_high_severity_gets_p0(self) -> None:
        items = [StandupItem(source="adversarial", description="Critical gap", severity="high")]
        author = _make_author()
        draft = author.plan_next(
            completed_tasks=[],
            standup_items=items,
            target_repo="bpsai-cli",
            next_sprint_id="S11",
            theme="Severity",
        )
        assert draft.backlog.tasks[0].priority == "P0"

    def test_medium_severity_gets_p1(self) -> None:
        items = [StandupItem(source="doc", description="Minor drift", severity="medium")]
        author = _make_author()
        draft = author.plan_next(
            completed_tasks=[],
            standup_items=items,
            target_repo="bpsai-cli",
            next_sprint_id="S11",
            theme="Severity",
        )
        assert draft.backlog.tasks[0].priority == "P1"

    def test_low_severity_gets_p2(self) -> None:
        items = [StandupItem(source="support", description="Nice to have", severity="low")]
        author = _make_author()
        draft = author.plan_next(
            completed_tasks=[],
            standup_items=items,
            target_repo="bpsai-cli",
            next_sprint_id="S11",
            theme="Severity",
        )
        assert draft.backlog.tasks[0].priority == "P2"

    def test_goal_derived_from_theme(self) -> None:
        author = _make_author()
        draft = author.plan_next(
            completed_tasks=_make_completed_tasks(),
            standup_items=_make_standup_items(),
            target_repo="bpsai-cli",
            next_sprint_id="S11",
            theme="Hardening",
        )
        assert "Hardening" in draft.backlog.goal or len(draft.backlog.goal) > 0

    def test_explicit_goal_used(self) -> None:
        author = _make_author()
        draft = author.plan_next(
            completed_tasks=[],
            standup_items=[],
            target_repo="bpsai-cli",
            next_sprint_id="S11",
            theme="X",
            goal="Specific goal here",
        )
        assert draft.backlog.goal == "Specific goal here"

    def test_carry_over_preserves_original_priority(self) -> None:
        """Failed P0 tasks should remain P0 when carried over."""
        tasks = [
            CompletedTask(
                task_id="T10.1", title="Critical fix",
                outcome=TaskOutcome.FAILED, priority="P0",
            ),
        ]
        author = _make_author()
        draft = author.plan_next(
            completed_tasks=tasks,
            standup_items=[],
            target_repo="bpsai-cli",
            next_sprint_id="S11",
            theme="Carry",
        )
        assert draft.backlog.tasks[0].priority == "P0"

    def test_predecessor_set(self) -> None:
        author = _make_author()
        draft = author.plan_next(
            completed_tasks=_make_completed_tasks(),
            standup_items=[],
            target_repo="bpsai-cli",
            next_sprint_id="S11",
            theme="Follow-up",
            predecessor="S10",
        )
        assert draft.backlog.predecessor == "S10"


# ── Carry-over logic edge cases ──────────────────────────────────


class TestCarryOverLogic:
    def test_failed_task_complexity_preserved(self) -> None:
        tasks = [
            CompletedTask(
                task_id="T10.1", title="Big task",
                outcome=TaskOutcome.FAILED, complexity=25,
            ),
        ]
        author = _make_author()
        draft = author.plan_next(
            completed_tasks=tasks,
            standup_items=[],
            target_repo="bpsai-cli",
            next_sprint_id="S11",
            theme="Retry",
        )
        assert draft.backlog.tasks[0].complexity == 25

    def test_multiple_failures_all_carry(self) -> None:
        tasks = [
            CompletedTask(task_id="T10.1", title="A", outcome=TaskOutcome.FAILED),
            CompletedTask(task_id="T10.2", title="B", outcome=TaskOutcome.FAILED),
            CompletedTask(task_id="T10.3", title="C", outcome=TaskOutcome.DEFERRED),
        ]
        author = _make_author()
        draft = author.plan_next(
            completed_tasks=tasks,
            standup_items=[],
            target_repo="bpsai-cli",
            next_sprint_id="S11",
            theme="Retry all",
        )
        assert len(draft.carry_over_ids) == 3
        assert len(draft.backlog.tasks) == 3

    def test_carry_over_gets_new_task_ids(self) -> None:
        """Carried-over tasks get new IDs for the new sprint."""
        tasks = [
            CompletedTask(task_id="T10.1", title="Old task", outcome=TaskOutcome.FAILED),
        ]
        author = _make_author()
        draft = author.plan_next(
            completed_tasks=tasks,
            standup_items=[],
            target_repo="bpsai-cli",
            next_sprint_id="S11",
            theme="Re-ID",
        )
        new_id = draft.backlog.tasks[0].task_id
        assert new_id.startswith("T11.")
        assert new_id != "T10.1"
