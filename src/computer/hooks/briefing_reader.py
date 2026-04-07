"""SENSE hook that reads the latest briefing from the #briefing channel."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from bpsai_agent_core.hook_protocols import BriefingSourceProtocol
from bpsai_agent_core.sense_event import SenseEvent, emit_sense_event
from bpsai_agent_core.tick import Phase, PhaseResult, TickContext

logger = logging.getLogger(__name__)

_STALE_THRESHOLD = timedelta(hours=24)


class BriefingReader:
    """Reads the latest briefing and populates state_snapshot."""

    def __init__(self, briefing_source: BriefingSourceProtocol) -> None:
        self._source = briefing_source

    @property
    def phase(self) -> Phase:
        return Phase.SENSE

    @property
    def priority(self) -> int:
        return 25

    async def execute(self, context: TickContext) -> PhaseResult:
        """Read latest briefing and inject into context."""
        try:
            briefing = self._source.get_latest_briefing()
        except Exception:
            logger.warning("Briefing channel error", exc_info=True)
            context.state_snapshot["metis_briefing"] = None
            emit_sense_event(context, SenseEvent(
                hook="BriefingReader",
                tick=context.tick_number,
                timestamp=context.timestamp,
                metrics={"briefing_found": False, "error": True},
            ))
            return PhaseResult(
                phase=Phase.SENSE,
                passed=True,
                findings=["Briefing channel error"],
                duration_ms=0.0,
            )

        if briefing is None:
            context.state_snapshot["metis_briefing"] = None
            emit_sense_event(context, SenseEvent(
                hook="BriefingReader",
                tick=context.tick_number,
                timestamp=context.timestamp,
                metrics={"briefing_found": False},
            ))
            return PhaseResult(
                phase=Phase.SENSE,
                passed=True,
                findings=["No briefing available"],
                duration_ms=0.0,
            )

        stale = self._is_stale(briefing.get("created_at", ""))
        briefing["stale"] = stale
        context.state_snapshot["metis_briefing"] = briefing

        emit_sense_event(context, SenseEvent(
            hook="BriefingReader",
            tick=context.tick_number,
            timestamp=context.timestamp,
            metrics={"briefing_found": True, "stale": stale},
        ))

        findings = ["Read latest briefing"]
        if stale:
            findings.append("Briefing is stale (>24h old)")
        return PhaseResult(
            phase=Phase.SENSE,
            passed=True,
            findings=findings,
            duration_ms=0.0,
        )

    @staticmethod
    def _is_stale(created_at: str) -> bool:
        """Return True if the briefing timestamp is older than 24 hours."""
        try:
            ts = datetime.fromisoformat(created_at)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) - ts > _STALE_THRESHOLD
        except (ValueError, TypeError):
            return True
