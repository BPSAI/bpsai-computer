"""Tests for the Computer outcome recorder LEARN hook."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from computer.hooks.outcome_recorder import OutcomeRecorder


class FakeJournal:
    def __init__(self) -> None:
        self.records: list[Any] = []

    def record(self, decision: Any) -> None:
        self.records.append(decision)


def _make_context(
    tick: int = 1,
    actions: list | None = None,
    findings: list | None = None,
) -> MagicMock:
    ctx = MagicMock()
    ctx.tick_number = tick
    ctx.timestamp = "2026-04-05T00:00:00Z"
    ctx.state_snapshot = {}
    if actions:
        ctx.state_snapshot["actions"] = actions
    if findings:
        ctx.state_snapshot["findings"] = findings
    return ctx


class TestOutcomeRecorder:
    @pytest.mark.asyncio
    async def test_no_actions(self) -> None:
        journal = FakeJournal()
        recorder = OutcomeRecorder(journal)
        ctx = _make_context()
        result = await recorder.execute(ctx)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_records_actions(self) -> None:
        journal = FakeJournal()
        recorder = OutcomeRecorder(journal)
        ctx = _make_context(actions=["fix bug", "deploy"])
        await recorder.execute(ctx)
        assert len(journal.records) == 2

    @pytest.mark.asyncio
    async def test_records_deferred_findings(self) -> None:
        journal = FakeJournal()
        recorder = OutcomeRecorder(journal)
        ctx = _make_context(actions=["fix bug"], findings=["fix bug", "tech debt"])
        await recorder.execute(ctx)
        # 1 dispatch (fix bug) + 1 defer (tech debt)
        assert len(journal.records) == 2

    @pytest.mark.asyncio
    async def test_idempotent(self) -> None:
        journal = FakeJournal()
        recorder = OutcomeRecorder(journal)
        ctx = _make_context(tick=1, actions=["a"])
        await recorder.execute(ctx)
        ctx2 = _make_context(tick=1, actions=["a"])
        await recorder.execute(ctx2)
        assert len(journal.records) == 1  # Second call skipped
