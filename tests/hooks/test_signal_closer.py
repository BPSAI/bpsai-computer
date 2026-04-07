"""Tests for the Computer signal closer LEARN hook."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from computer.hooks.signal_closer import SignalCloser


class FakeSignal:
    def __init__(self, signal_id: str, action: str) -> None:
        self.signal_id = signal_id
        self.action = action


class FakeStore:
    def __init__(self, signals: list) -> None:
        self._signals = signals
        self.closed: list[tuple[str, str]] = []

    def list_active(self) -> list:
        return self._signals

    def close(self, signal_id: str, reason: str) -> None:
        self.closed.append((signal_id, reason))


def _make_context(tick: int = 1, completed: list | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.tick_number = tick
    ctx.timestamp = "2026-04-05T00:00:00Z"
    ctx.state_snapshot = {}
    if completed:
        ctx.state_snapshot["completed_tasks"] = completed
    return ctx


class TestSignalCloser:
    @pytest.mark.asyncio
    async def test_no_completed_tasks(self) -> None:
        store = FakeStore([FakeSignal("SIG-001", "T1.1")])
        closer = SignalCloser(store)
        ctx = _make_context()
        result = await closer.execute(ctx)
        assert result.passed is True
        assert store.closed == []

    @pytest.mark.asyncio
    async def test_closes_matching_signal(self) -> None:
        store = FakeStore([FakeSignal("SIG-001", "T1.1")])
        closer = SignalCloser(store)
        ctx = _make_context(completed=["T1.1"])
        await closer.execute(ctx)
        assert len(store.closed) == 1
        assert store.closed[0][0] == "SIG-001"

    @pytest.mark.asyncio
    async def test_emits_learn_telemetry(self) -> None:
        closer = SignalCloser(FakeStore([]))
        ctx = _make_context()
        await closer.execute(ctx)
        assert ctx.state_snapshot["learn_telemetry"][0]["hook"] == "SignalCloser"
