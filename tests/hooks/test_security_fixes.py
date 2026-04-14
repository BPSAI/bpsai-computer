"""Tests for P2 security fixes: SEC-003, SEC-004, SEC-005."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.orchestration.models import Phase, PhaseResult, TickContext, TickResult
from engine.signal_types import Signal
from engine.hypothesis_types import Hypothesis, HypothesisStatus
from engine.idea_store import IdeaStore
from computer.hooks.idea_recorder import IdeaRecorder
from computer.hooks.idea_observer import IdeaObserverHook


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_context(tick: int = 1, **snapshot_kw: object) -> TickContext:
    prev = TickResult(
        tick_number=0,
        phase_results={
            "sense": PhaseResult(
                phase=Phase.SENSE, passed=True,
                findings=[], duration_ms=1.0,
            ),
        },
        duration_ms=1.0,
        events_processed=0,
    )
    return TickContext(
        tick_number=tick,
        timestamp="2026-03-26T00:00:00Z",
        event_queue_snapshot=[],
        state_snapshot=dict(snapshot_kw),
        previous_result=prev,
    )


# ---------------------------------------------------------------------------
# SEC-004: Signal Literal validation
# ---------------------------------------------------------------------------

class TestSignalFromDictValidation:
    """Signal.from_dict rejects invalid attribution and category."""

    def test_invalid_attribution_raises(self) -> None:
        data = {
            "signal_id": "SIG-001",
            "date": "2026-03-26",
            "attribution": "hacker",
            "category": "estimation",
            "observation": "obs",
            "evidence": "ev",
            "root_cause": "rc",
            "action": "act",
        }
        with pytest.raises(ValueError, match="attribution"):
            Signal.from_dict(data)

    def test_invalid_category_raises(self) -> None:
        data = {
            "signal_id": "SIG-001",
            "date": "2026-03-26",
            "attribution": "cns",
            "category": "hacking",
            "observation": "obs",
            "evidence": "ev",
            "root_cause": "rc",
            "action": "act",
        }
        with pytest.raises(ValueError, match="category"):
            Signal.from_dict(data)

    def test_valid_values_accepted(self) -> None:
        """All valid attribution/category combinations work."""
        for attr in ("cns", "tool", "both"):
            for cat in ("estimation", "duplication", "planning", "coordination"):
                data = {
                    "signal_id": "SIG-001",
                    "date": "2026-03-26",
                    "attribution": attr,
                    "category": cat,
                    "observation": "obs",
                    "evidence": "ev",
                    "root_cause": "rc",
                    "action": "act",
                }
                sig = Signal.from_dict(data)
                assert sig.attribution == attr
                assert sig.category == cat


# ---------------------------------------------------------------------------
# SEC-004: Hypothesis free-text max-length guards
# ---------------------------------------------------------------------------

class TestHypothesisFromDictMaxLength:
    """Hypothesis.from_dict truncates oversized free-text fields."""

    def test_oversized_pattern_truncated(self) -> None:
        long_text = "x" * 2000
        data = {
            "hyp_id": "HYP-001",
            "observed_date": "2026-03-26",
            "pattern": long_text,
            "options": [],
            "current_signal": "",
            "instrumentation_needed": "",
            "re_evaluate_after": "2026-04-26",
        }
        h = Hypothesis.from_dict(data)
        assert len(h.pattern) <= 1024

    def test_oversized_instrumentation_needed_truncated(self) -> None:
        long_text = "y" * 2000
        data = {
            "hyp_id": "HYP-002",
            "observed_date": "2026-03-26",
            "pattern": "ok",
            "options": [],
            "current_signal": "",
            "instrumentation_needed": long_text,
            "re_evaluate_after": "2026-04-26",
        }
        h = Hypothesis.from_dict(data)
        assert len(h.instrumentation_needed) <= 1024

    def test_oversized_observation_field_truncated(self) -> None:
        """The 'observation' field maps to current_signal in the dict."""
        # Note: The spec says 'observation' field. In the Hypothesis dataclass
        # there is no 'observation' field, but current_signal is a free-text.
        # We guard current_signal as the closest match.
        long_text = "z" * 2000
        data = {
            "hyp_id": "HYP-003",
            "observed_date": "2026-03-26",
            "pattern": "ok",
            "options": [],
            "current_signal": long_text,
            "instrumentation_needed": "",
            "re_evaluate_after": "2026-04-26",
        }
        h = Hypothesis.from_dict(data)
        assert len(h.current_signal) <= 1024

    def test_normal_length_unchanged(self) -> None:
        data = {
            "hyp_id": "HYP-004",
            "observed_date": "2026-03-26",
            "pattern": "short pattern",
            "options": [],
            "current_signal": "SIG-001",
            "instrumentation_needed": "some instrumentation",
            "re_evaluate_after": "2026-04-26",
        }
        h = Hypothesis.from_dict(data)
        assert h.pattern == "short pattern"
        assert h.instrumentation_needed == "some instrumentation"


# ---------------------------------------------------------------------------
# SEC-005: IdeaRecorder body length cap
# ---------------------------------------------------------------------------

class TestIdeaRecorderBodyTruncation:
    """IdeaRecorder truncates long observation bodies."""

    @pytest.mark.asyncio
    async def test_truncates_long_observation(self, tmp_path: Path) -> None:
        idea_store = IdeaStore(tmp_path / "ideas.jsonl")
        hook = IdeaRecorder(idea_store)
        long_body = "a" * 8000
        ctx = _make_context(
            observations=[long_body],
            signal_ids=[],
            hypothesis_ids=[],
        )
        await hook.execute(ctx)
        ideas = idea_store.list_by_status("observed")
        assert len(ideas) == 1
        assert len(ideas[0].body) <= 4096

    @pytest.mark.asyncio
    async def test_normal_observation_unchanged(self, tmp_path: Path) -> None:
        idea_store = IdeaStore(tmp_path / "ideas.jsonl")
        hook = IdeaRecorder(idea_store)
        normal_body = "normal observation"
        ctx = _make_context(
            observations=[normal_body],
            signal_ids=[],
            hypothesis_ids=[],
        )
        await hook.execute(ctx)
        ideas = idea_store.list_by_status("observed")
        assert len(ideas) == 1
        assert ideas[0].body == normal_body


# ---------------------------------------------------------------------------
# SEC-005: IdeaObserverHook body length cap
# ---------------------------------------------------------------------------

class TestIdeaObserverBodyTruncation:
    """IdeaObserverHook truncates long finding bodies."""

    @pytest.mark.asyncio
    async def test_truncates_long_finding(self, tmp_path: Path) -> None:
        idea_store = IdeaStore(tmp_path / "ideas.jsonl")
        hook = IdeaObserverHook(idea_store)
        long_finding = "b" * 8000
        ctx = _make_context(findings=[long_finding])
        await hook.execute(ctx)
        ideas = idea_store.list_by_status("observed")
        assert len(ideas) == 1
        assert len(ideas[0].body) <= 4096

    @pytest.mark.asyncio
    async def test_normal_finding_unchanged(self, tmp_path: Path) -> None:
        idea_store = IdeaStore(tmp_path / "ideas.jsonl")
        hook = IdeaObserverHook(idea_store)
        normal = "short finding"
        ctx = _make_context(findings=[normal])
        await hook.execute(ctx)
        ideas = idea_store.list_by_status("observed")
        assert len(ideas) == 1
        assert ideas[0].body == normal
