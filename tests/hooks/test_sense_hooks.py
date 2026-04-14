"""Tests for SENSE phase hooks: IdeaObserverHook.

Pattern detector tests migrated to paircoder_bot with the hooks.
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any

import pytest

from engine.orchestration.models import Phase, TickContext


def _make_context(state: dict[str, Any] | None = None) -> TickContext:
    return TickContext(
        tick_number=0,
        timestamp="2026-03-26T00:00:00+00:00",
        event_queue_snapshot=[],
        state_snapshot=state or {},
    )


class TestIdeaObserverHook:
    """IdeaObserverHook captures findings as ideas."""

    def test_implements_phase_hook_protocol(self) -> None:
        from engine.orchestration.phase_registry import PhaseHook
        from computer.hooks.idea_observer import IdeaObserverHook
        store = self._make_store()
        hook = IdeaObserverHook(idea_store=store)
        assert isinstance(hook, PhaseHook)

    def test_phase_is_sense(self) -> None:
        from computer.hooks.idea_observer import IdeaObserverHook
        hook = IdeaObserverHook(idea_store=self._make_store())
        assert hook.phase == Phase.SENSE

    def test_priority_is_50(self) -> None:
        from computer.hooks.idea_observer import IdeaObserverHook
        hook = IdeaObserverHook(idea_store=self._make_store())
        assert hook.priority == 50

    def test_no_findings_no_ideas(self) -> None:
        from computer.hooks.idea_observer import IdeaObserverHook
        store = self._make_store()
        hook = IdeaObserverHook(idea_store=store)
        context = _make_context({"findings": []})
        result = asyncio.run(hook.execute(context))
        assert result.passed is True
        assert store.list_by_status("observed") == []

    def test_findings_captured_as_ideas(self) -> None:
        from computer.hooks.idea_observer import IdeaObserverHook
        store = self._make_store()
        hook = IdeaObserverHook(idea_store=store)
        context = _make_context({
            "findings": [
                "Failure concentration in estimation (80%)",
                "Stale hypothesis HYP-001 past re-evaluation",
            ],
        })
        asyncio.run(hook.execute(context))
        ideas = store.list_by_status("observed")
        assert len(ideas) == 2
        assert ideas[0].source == "agent"
        assert ideas[0].created_by == "pattern_detector"
        assert "estimation" in ideas[0].body

    def test_ideas_tagged_with_sense(self) -> None:
        from computer.hooks.idea_observer import IdeaObserverHook
        store = self._make_store()
        hook = IdeaObserverHook(idea_store=store)
        context = _make_context({"findings": ["Some finding"]})
        asyncio.run(hook.execute(context))
        ideas = store.list_by_status("observed")
        assert "sense" in ideas[0].tags

    def test_findings_count_in_phase_result(self) -> None:
        from computer.hooks.idea_observer import IdeaObserverHook
        store = self._make_store()
        hook = IdeaObserverHook(idea_store=store)
        context = _make_context({"findings": ["F1", "F2"]})
        result = asyncio.run(hook.execute(context))
        assert len(result.findings) == 1
        assert "2" in result.findings[0]

    def test_idempotent_same_tick(self) -> None:
        from computer.hooks.idea_observer import IdeaObserverHook
        store = self._make_store()
        hook = IdeaObserverHook(idea_store=store)
        context = _make_context({"findings": ["Finding A"]})
        asyncio.run(hook.execute(context))
        count_first = len(store.list_by_status("observed"))
        asyncio.run(hook.execute(context))
        count_second = len(store.list_by_status("observed"))
        assert count_second == count_first

    def test_missing_findings_key_graceful(self) -> None:
        from computer.hooks.idea_observer import IdeaObserverHook
        store = self._make_store()
        hook = IdeaObserverHook(idea_store=store)
        context = _make_context({})
        result = asyncio.run(hook.execute(context))
        assert result.passed is True

    def test_exports_from_package(self) -> None:
        from engine.orchestration.sense import IdeaObserverHook
        assert IdeaObserverHook is not None

    def _make_store(self, tmp_path: Path | None = None) -> Any:
        from engine.idea_store import IdeaStore
        if tmp_path is None:
            tmp_path = Path(tempfile.mkdtemp())
        return IdeaStore(tmp_path / "test_ideas.jsonl")
