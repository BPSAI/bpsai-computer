"""Tests for engine.orchestration.learn -- LEARN phase hooks.

Tests for migrated hooks (OutcomeRecorder, HypothesisUpdater,
SignalCloser) now live in their respective owner repos.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.idea_store import IdeaStore
from engine.orchestration.models import (
    Phase,
    PhaseResult,
    TickContext,
    TickResult,
)
from engine.orchestration.phase_registry import PhaseHook

from computer.hooks.idea_recorder import IdeaRecorder


def _make_tick_context(
    *,
    observations: list[str] | None = None,
    signal_ids: list[str] | None = None,
    hypothesis_ids: list[str] | None = None,
) -> TickContext:
    """Build a TickContext with state_snapshot data for learn hooks."""
    state: dict = {}
    if observations is not None:
        state["observations"] = observations
    if signal_ids is not None:
        state["signal_ids"] = signal_ids
    if hypothesis_ids is not None:
        state["hypothesis_ids"] = hypothesis_ids

    prev = TickResult(
        tick_number=0,
        phase_results={
            "sense": PhaseResult(
                phase=Phase.SENSE, passed=True,
                findings=[], duration_ms=1.0,
            ),
        },
        duration_ms=10.0,
        events_processed=0,
    )
    return TickContext(
        tick_number=1,
        timestamp="2026-03-26T00:00:00Z",
        event_queue_snapshot=[],
        state_snapshot=state,
        previous_result=prev,
    )


class TestIdeaRecorderProtocol:
    """IdeaRecorder conforms to PhaseHook protocol."""

    def test_is_phase_hook(self, tmp_path: Path) -> None:
        idea_store = IdeaStore(tmp_path / "i.jsonl")
        hook = IdeaRecorder(idea_store)
        assert isinstance(hook, PhaseHook)

    def test_phase_is_learn(self, tmp_path: Path) -> None:
        idea_store = IdeaStore(tmp_path / "i.jsonl")
        hook = IdeaRecorder(idea_store)
        assert hook.phase == Phase.LEARN

    def test_priority_is_40(self, tmp_path: Path) -> None:
        idea_store = IdeaStore(tmp_path / "i.jsonl")
        hook = IdeaRecorder(idea_store)
        assert hook.priority == 40


class TestIdeaRecorderExecute:
    """IdeaRecorder captures observations as ideas."""

    @pytest.mark.asyncio
    async def test_creates_idea_from_observation(
        self, tmp_path: Path,
    ) -> None:
        idea_store = IdeaStore(tmp_path / "i.jsonl")
        hook = IdeaRecorder(idea_store)
        ctx = _make_tick_context(
            observations=["interesting pattern detected"],
            signal_ids=["SIG-001"],
            hypothesis_ids=["HYP-001"],
        )
        result = await hook.execute(ctx)
        assert result.passed is True
        ideas = idea_store.list_by_status("observed")
        assert len(ideas) == 1
        assert ideas[0].source == "computer"
        assert "interesting pattern detected" in ideas[0].body
        assert "SIG-001" in ideas[0].linked_signals
        assert ideas[0].linked_hypothesis == "HYP-001"

    @pytest.mark.asyncio
    async def test_no_observations_is_noop(
        self, tmp_path: Path,
    ) -> None:
        idea_store = IdeaStore(tmp_path / "i.jsonl")
        hook = IdeaRecorder(idea_store)
        ctx = _make_tick_context(observations=[])
        result = await hook.execute(ctx)
        assert result.passed is True
        assert len(idea_store.list_by_status("observed")) == 0

    @pytest.mark.asyncio
    async def test_idempotent(self, tmp_path: Path) -> None:
        idea_store = IdeaStore(tmp_path / "i.jsonl")
        hook = IdeaRecorder(idea_store)
        ctx = _make_tick_context(
            observations=["pattern A"],
            signal_ids=[],
            hypothesis_ids=[],
        )
        await hook.execute(ctx)
        count_first = len(idea_store.list_by_status("observed"))
        await hook.execute(ctx)
        count_second = len(idea_store.list_by_status("observed"))
        assert count_second == count_first

    @pytest.mark.asyncio
    async def test_multiple_observations(
        self, tmp_path: Path,
    ) -> None:
        idea_store = IdeaStore(tmp_path / "i.jsonl")
        hook = IdeaRecorder(idea_store)
        ctx = _make_tick_context(
            observations=["pattern A", "pattern B"],
            signal_ids=["SIG-001"],
        )
        await hook.execute(ctx)
        ideas = idea_store.list_by_status("observed")
        assert len(ideas) == 2


