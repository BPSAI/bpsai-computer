"""Tests for LEARN hook observability signal emission (TH3.2).

Tests for migrated hooks (OutcomeRecorder, DispatchOutcomeHook,
HypothesisUpdater, SignalCloser) now live in their respective repos.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from engine.idea_store import IdeaStore
from computer.hooks.idea_recorder import IdeaRecorder
from engine.orchestration.learn.learn_event import LearnEvent, emit_learn_event
from engine.orchestration.models import TickContext


def _make_context(tick: int = 1, state: dict[str, Any] | None = None) -> TickContext:
    return TickContext(
        tick_number=tick,
        timestamp="2026-03-26T00:00:00+00:00",
        event_queue_snapshot=[],
        state_snapshot=state or {},
    )


class TestLearnEvent:
    """LearnEvent dataclass and helpers."""

    def test_to_dict_roundtrip(self) -> None:
        event = LearnEvent(hook="TestHook", tick=5, timestamp="2026-03-26T00:00:00+00:00", metrics={"count": 3})
        d = event.to_dict()
        restored = LearnEvent.from_dict(d)
        assert restored.hook == "TestHook"
        assert restored.tick == 5
        assert restored.metrics == {"count": 3}

    def test_emit_learn_event_creates_list(self) -> None:
        ctx = _make_context()
        event = LearnEvent(hook="X", tick=1, timestamp="t", metrics={})
        emit_learn_event(ctx, event)
        assert len(ctx.state_snapshot["learn_telemetry"]) == 1

    def test_emit_learn_event_appends(self) -> None:
        ctx = _make_context()
        emit_learn_event(ctx, LearnEvent(hook="A", tick=1, timestamp="t", metrics={}))
        emit_learn_event(ctx, LearnEvent(hook="B", tick=1, timestamp="t", metrics={}))
        assert len(ctx.state_snapshot["learn_telemetry"]) == 2


class TestIdeaRecorderTelemetry:
    """IdeaRecorder emits telemetry about ideas recorded."""

    @pytest.mark.asyncio
    async def test_emits_learn_event(self, tmp_path: Path) -> None:
        store = IdeaStore(tmp_path / "ideas.jsonl")
        hook = IdeaRecorder(idea_store=store)
        ctx = _make_context(tick=5, state={
            "observations": ["obs1", "obs2", "obs3"],
            "signal_ids": ["SIG-1"],
            "hypothesis_ids": [],
        })

        await hook.execute(ctx)

        telemetry = ctx.state_snapshot["learn_telemetry"]
        assert len(telemetry) == 1
        evt = telemetry[0]
        assert evt["hook"] == "IdeaRecorder"
        assert evt["tick"] == 5
        assert evt["metrics"]["ideas_recorded"] == 3

    @pytest.mark.asyncio
    async def test_empty_observations_telemetry(self, tmp_path: Path) -> None:
        store = IdeaStore(tmp_path / "ideas.jsonl")
        hook = IdeaRecorder(idea_store=store)
        ctx = _make_context(tick=1, state={})

        await hook.execute(ctx)

        evt = ctx.state_snapshot["learn_telemetry"][0]
        assert evt["metrics"]["ideas_recorded"] == 0

    @pytest.mark.asyncio
    async def test_duplicate_tick_telemetry(self, tmp_path: Path) -> None:
        store = IdeaStore(tmp_path / "ideas.jsonl")
        hook = IdeaRecorder(idea_store=store)
        ctx = _make_context(tick=5, state={"observations": ["obs1"]})

        await hook.execute(ctx)
        await hook.execute(ctx)

        telemetry = ctx.state_snapshot["learn_telemetry"]
        assert len(telemetry) == 2
        assert telemetry[1]["metrics"]["skipped_duplicate_tick"] is True
        assert telemetry[1]["metrics"]["ideas_recorded"] == 0
