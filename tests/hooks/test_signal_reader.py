"""Tests for the Computer signal reader SENSE hook."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from computer.hooks.signal_reader import SignalStoreReader


def _make_context(tick: int = 1) -> MagicMock:
    ctx = MagicMock()
    ctx.tick_number = tick
    ctx.timestamp = "2026-04-05T00:00:00Z"
    ctx.state_snapshot = {}
    return ctx


class FakeSignal:
    def __init__(self, signal_id: str) -> None:
        self.signal_id = signal_id

    def to_dict(self) -> dict:
        return {"signal_id": self.signal_id}


class FakeStore:
    def __init__(self, signals: list) -> None:
        self._signals = signals

    def list_active(self) -> list:
        return self._signals

    def close(self, signal_id: str, reason: str) -> None:
        pass


class TestSignalStoreReader:
    @pytest.mark.asyncio
    async def test_empty_store(self) -> None:
        reader = SignalStoreReader(FakeStore([]))
        ctx = _make_context()
        result = await reader.execute(ctx)
        assert result.passed is True
        assert ctx.state_snapshot["signals"] == []

    @pytest.mark.asyncio
    async def test_reads_active_signals(self) -> None:
        store = FakeStore([FakeSignal("SIG-001"), FakeSignal("SIG-002")])
        reader = SignalStoreReader(store)
        ctx = _make_context()
        await reader.execute(ctx)
        assert len(ctx.state_snapshot["signals"]) == 2

    @pytest.mark.asyncio
    async def test_emits_sense_telemetry(self) -> None:
        reader = SignalStoreReader(FakeStore([]))
        ctx = _make_context()
        await reader.execute(ctx)
        assert ctx.state_snapshot["sense_telemetry"][0]["hook"] == "SignalStoreReader"
