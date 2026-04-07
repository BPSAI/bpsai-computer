"""Tests for the Computer briefing reader SENSE hook."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from computer.hooks.briefing_reader import BriefingReader


def _make_context(tick: int = 1) -> MagicMock:
    ctx = MagicMock()
    ctx.tick_number = tick
    ctx.timestamp = "2026-04-05T00:00:00Z"
    ctx.state_snapshot = {}
    return ctx


class FakeSource:
    def __init__(self, briefing: dict[str, Any] | None = None) -> None:
        self._briefing = briefing

    def get_latest_briefing(self) -> dict[str, Any] | None:
        return self._briefing


class ErrorSource:
    def get_latest_briefing(self) -> dict[str, Any] | None:
        raise RuntimeError("channel down")


class TestBriefingReader:
    @pytest.mark.asyncio
    async def test_no_briefing(self) -> None:
        reader = BriefingReader(FakeSource(None))
        ctx = _make_context()
        result = await reader.execute(ctx)
        assert result.passed is True
        assert ctx.state_snapshot["metis_briefing"] is None

    @pytest.mark.asyncio
    async def test_fresh_briefing(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        reader = BriefingReader(FakeSource({"content": "hi", "created_at": now}))
        ctx = _make_context()
        result = await reader.execute(ctx)
        assert ctx.state_snapshot["metis_briefing"]["stale"] is False

    @pytest.mark.asyncio
    async def test_stale_briefing(self) -> None:
        reader = BriefingReader(FakeSource({"content": "hi", "created_at": "2020-01-01T00:00:00Z"}))
        ctx = _make_context()
        await reader.execute(ctx)
        assert ctx.state_snapshot["metis_briefing"]["stale"] is True

    @pytest.mark.asyncio
    async def test_error_handling(self) -> None:
        reader = BriefingReader(ErrorSource())
        ctx = _make_context()
        result = await reader.execute(ctx)
        assert result.passed is True
        assert ctx.state_snapshot["metis_briefing"] is None
