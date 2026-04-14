"""Tests for SENSE hook observability signal emission (TH3.1).

Tests for migrated hooks (SignalStoreReader, HypothesisScanner,
PortfolioStateReader, PatternDetectorHook) now live in their
respective owner repos.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest

from engine.idea_store import IdeaStore
from engine.orchestration.models import TickContext
from computer.hooks.idea_observer import IdeaObserverHook
from engine.orchestration.sense.sense_event import SenseEvent, emit_sense_event


def _make_context(tick: int = 1, state: dict[str, Any] | None = None) -> TickContext:
    return TickContext(
        tick_number=tick,
        timestamp="2026-03-26T00:00:00+00:00",
        event_queue_snapshot=[],
        state_snapshot=state or {},
    )


class TestSenseEvent:
    """SenseEvent dataclass and helpers."""

    def test_to_dict_roundtrip(self) -> None:
        event = SenseEvent(hook="TestHook", tick=5, timestamp="2026-03-26T00:00:00+00:00", metrics={"count": 3})
        d = event.to_dict()
        restored = SenseEvent.from_dict(d)
        assert restored.hook == "TestHook"
        assert restored.tick == 5
        assert restored.metrics == {"count": 3}

    def test_emit_sense_event_creates_list(self) -> None:
        ctx = _make_context()
        event = SenseEvent(hook="X", tick=1, timestamp="t", metrics={})
        emit_sense_event(ctx, event)
        assert len(ctx.state_snapshot["sense_telemetry"]) == 1

    def test_emit_sense_event_appends(self) -> None:
        ctx = _make_context()
        emit_sense_event(ctx, SenseEvent(hook="A", tick=1, timestamp="t", metrics={}))
        emit_sense_event(ctx, SenseEvent(hook="B", tick=1, timestamp="t", metrics={}))
        assert len(ctx.state_snapshot["sense_telemetry"]) == 2


class TestIdeaObserverHookTelemetry:
    """IdeaObserverHook emits telemetry about ideas captured."""

    def _make_store(self) -> Any:
        return IdeaStore(Path(tempfile.mkdtemp()) / "ideas.jsonl")

    @pytest.mark.asyncio
    async def test_emits_sense_event(self) -> None:
        store = self._make_store()
        hook = IdeaObserverHook(idea_store=store)
        ctx = _make_context(tick=5, state={"findings": ["F1", "F2", "F3"]})

        await hook.execute(ctx)

        telemetry = ctx.state_snapshot["sense_telemetry"]
        assert len(telemetry) == 1
        evt = telemetry[0]
        assert evt["hook"] == "IdeaObserverHook"
        assert evt["tick"] == 5
        assert evt["metrics"]["ideas_captured"] == 3
        assert evt["metrics"]["skipped_duplicate_tick"] is False

    @pytest.mark.asyncio
    async def test_duplicate_tick_telemetry(self) -> None:
        store = self._make_store()
        hook = IdeaObserverHook(idea_store=store)
        ctx = _make_context(tick=5, state={"findings": ["F1"]})

        await hook.execute(ctx)
        await hook.execute(ctx)

        telemetry = ctx.state_snapshot["sense_telemetry"]
        assert len(telemetry) == 2
        assert telemetry[1]["metrics"]["skipped_duplicate_tick"] is True
        assert telemetry[1]["metrics"]["ideas_captured"] == 0
