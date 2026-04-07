"""SENSE hook that reads portfolio state from status.yaml and sprint-plan.md."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from bpsai_agent_core.sense_event import SenseEvent, emit_sense_event
from bpsai_agent_core.tick import Phase, PhaseResult, TickContext


class PortfolioStateReader:
    """Reads portfolio files and populates state_snapshot.

    Reads ``status.yaml`` and ``sprint-plan.md`` from a configurable
    directory. Missing files are treated gracefully (set to None).
    """

    def __init__(self, portfolio_dir: Path) -> None:
        self._dir = Path(portfolio_dir).resolve()

    @property
    def phase(self) -> Phase:
        return Phase.SENSE

    @property
    def priority(self) -> int:
        return 30

    async def execute(self, context: TickContext) -> PhaseResult:
        """Read portfolio files and inject into context."""
        status = self._read_status()
        sprint_plan = self._read_sprint_plan()
        context.state_snapshot["portfolio"] = {
            "status": status,
            "sprint_plan": sprint_plan,
        }
        emit_sense_event(context, SenseEvent(
            hook="PortfolioStateReader",
            tick=context.tick_number,
            timestamp=context.timestamp,
            metrics={
                "status_loaded": status is not None,
                "sprint_plan_loaded": sprint_plan is not None,
            },
        ))
        findings = []
        if status is not None:
            findings.append("Read status.yaml")
        if sprint_plan is not None:
            findings.append("Read sprint-plan.md")
        if not findings:
            findings.append("No portfolio files found")
        return PhaseResult(
            phase=Phase.SENSE,
            passed=True,
            findings=findings,
            duration_ms=0.0,
        )

    def _read_status(self) -> dict[str, Any] | None:
        """Parse status.yaml if it exists."""
        path = self._dir / "status.yaml"
        if not path.exists():
            return None
        try:
            return yaml.safe_load(path.read_text())
        except yaml.YAMLError:
            return None

    def _read_sprint_plan(self) -> str | None:
        """Read sprint-plan.md if it exists."""
        path = self._dir / "sprint-plan.md"
        if not path.exists():
            return None
        return path.read_text()
