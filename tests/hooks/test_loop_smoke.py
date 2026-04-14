"""LS0.2 -- Smoke test: wire remaining hooks, run one tick, validate basics.

Migrated hooks (signal_reader, hypothesis_scanner, portfolio_reader,
pattern_detector, outcome_recorder, hypothesis_updater, signal_closer)
now live in their owner repos. This test validates the framework-owned
hooks (IdeaObserverHook, IdeaRecorder) work within the loop.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from engine.idea_store import IdeaStore
from engine.orchestration.cadence import StaticCadenceResolver
from engine.orchestration.event_queue import EventQueue
from engine.orchestration.loop_runner import LoopRunner
from engine.orchestration.models import Phase
from engine.orchestration.phase_registry import PhaseRegistry
from computer.hooks.idea_observer import IdeaObserverHook
from computer.hooks.idea_recorder import IdeaRecorder


def _build_registry(
    idea_store: IdeaStore,
) -> PhaseRegistry:
    """Register remaining framework-owned hooks."""
    registry = PhaseRegistry()
    registry.register(IdeaObserverHook(idea_store))
    registry.register(IdeaRecorder(idea_store))
    return registry


@pytest.fixture()
def smoke_env(tmp_path: Path):
    """Set up minimal data, run one tick, return post-tick state."""
    idea_store = IdeaStore(tmp_path / "ideas.jsonl")
    registry = _build_registry(idea_store)
    cadence = StaticCadenceResolver.from_config({})
    runner = LoopRunner(registry, cadence, EventQueue())
    result = asyncio.run(runner.run_tick())
    return {
        "result": result,
        "registry": registry,
        "idea_store": idea_store,
    }


class TestLoopSmoke:
    """LS0.2: Minimal smoke -- does a tick complete?"""

    def test_registry_has_hooks(self, smoke_env) -> None:
        """PhaseRegistry contains the 2 framework-owned hooks."""
        assert smoke_env["registry"].count() >= 2

    def test_single_tick_completes(self, smoke_env) -> None:
        """Single tick completes without error."""
        result = smoke_env["result"]
        assert result.tick_number >= 0
        assert result.duration_ms >= 0

    def test_tick_duration_non_negative(self, smoke_env) -> None:
        """Tick reports a non-negative duration."""
        assert smoke_env["result"].duration_ms >= 0
