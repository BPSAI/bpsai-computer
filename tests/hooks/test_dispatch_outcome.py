"""Tests for the Computer dispatch outcome LEARN hook."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from computer.hooks.dispatch_outcome_hook import DispatchOutcomeHook


def _make_context(tick: int = 1, outcomes: list | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.tick_number = tick
    ctx.timestamp = "2026-04-05T00:00:00Z"
    ctx.state_snapshot = {}
    if outcomes:
        ctx.state_snapshot["dispatch_outcomes"] = outcomes
    return ctx


class TestDispatchOutcomeHook:
    @pytest.mark.asyncio
    async def test_no_outcomes(self) -> None:
        hook = DispatchOutcomeHook()
        ctx = _make_context()
        result = await hook.execute(ctx)
        assert result.passed is True
        assert result.findings == []

    @pytest.mark.asyncio
    async def test_processes_outcomes(self) -> None:
        hook = DispatchOutcomeHook()
        ctx = _make_context(outcomes=[
            {"session_id": "s1", "status": "done", "backlog_id": "B1"},
        ])
        result = await hook.execute(ctx)
        assert len(result.findings) == 1
        assert "s1" in result.findings[0]

    @pytest.mark.asyncio
    async def test_idempotent(self) -> None:
        hook = DispatchOutcomeHook()
        ctx1 = _make_context(tick=1, outcomes=[
            {"session_id": "s1", "status": "done", "backlog_id": "B1"},
        ])
        await hook.execute(ctx1)
        ctx2 = _make_context(tick=1, outcomes=[
            {"session_id": "s1", "status": "done", "backlog_id": "B1"},
        ])
        result = await hook.execute(ctx2)
        # Second call returns cached findings
        assert result.passed is True
