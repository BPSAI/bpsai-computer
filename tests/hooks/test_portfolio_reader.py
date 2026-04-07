"""Tests for the Computer portfolio reader SENSE hook."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from computer.hooks.portfolio_reader import PortfolioStateReader


def _make_context(tick: int = 1) -> MagicMock:
    ctx = MagicMock()
    ctx.tick_number = tick
    ctx.timestamp = "2026-04-05T00:00:00Z"
    ctx.state_snapshot = {}
    return ctx


class TestPortfolioStateReader:
    @pytest.mark.asyncio
    async def test_missing_dir(self, tmp_path: Path) -> None:
        reader = PortfolioStateReader(tmp_path / "nonexistent")
        ctx = _make_context()
        result = await reader.execute(ctx)
        assert result.passed is True
        portfolio = ctx.state_snapshot["portfolio"]
        assert portfolio["status"] is None
        assert portfolio["sprint_plan"] is None

    @pytest.mark.asyncio
    async def test_reads_status_yaml(self, tmp_path: Path) -> None:
        (tmp_path / "status.yaml").write_text("test_count: 100\n")
        reader = PortfolioStateReader(tmp_path)
        ctx = _make_context()
        await reader.execute(ctx)
        assert ctx.state_snapshot["portfolio"]["status"]["test_count"] == 100

    @pytest.mark.asyncio
    async def test_reads_sprint_plan(self, tmp_path: Path) -> None:
        (tmp_path / "sprint-plan.md").write_text("# Sprint Plan\n")
        reader = PortfolioStateReader(tmp_path)
        ctx = _make_context()
        await reader.execute(ctx)
        assert "Sprint Plan" in ctx.state_snapshot["portfolio"]["sprint_plan"]
