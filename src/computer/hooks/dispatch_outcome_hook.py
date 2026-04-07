"""LEARN hook: records dispatch outcomes for calibration."""

from __future__ import annotations

from bpsai_agent_core.learn_event import LearnEvent, emit_learn_event
from bpsai_agent_core.tick import Phase, PhaseResult, TickContext


class DispatchOutcomeHook:
    """Records dispatch outcomes for calibration data."""

    def __init__(self) -> None:
        self._processed_ticks: set[int] = set()
        self._last_findings: dict[int, list[str]] = {}

    @property
    def phase(self) -> Phase:
        return Phase.LEARN

    @property
    def priority(self) -> int:
        return 15

    async def execute(self, context: TickContext) -> PhaseResult:
        if context.tick_number in self._processed_ticks:
            emit_learn_event(context, LearnEvent(
                hook="DispatchOutcomeHook",
                tick=context.tick_number,
                timestamp=context.timestamp,
                metrics={
                    "skipped_duplicate_tick": True,
                    "outcomes_processed": 0,
                },
            ))
            return PhaseResult(
                phase=Phase.LEARN, passed=True,
                findings=self._last_findings.get(context.tick_number, []),
                duration_ms=0.0,
            )
        self._processed_ticks.add(context.tick_number)

        outcomes = context.state_snapshot.get("dispatch_outcomes", [])
        findings: list[str] = []
        for outcome in outcomes:
            sid = outcome.get("session_id", "unknown")
            status = outcome.get("status", "unknown")
            backlog_id = outcome.get("backlog_id", "?")
            findings.append(f"Dispatch {sid} ({backlog_id}): {status}")

        self._last_findings[context.tick_number] = findings

        emit_learn_event(context, LearnEvent(
            hook="DispatchOutcomeHook",
            tick=context.tick_number,
            timestamp=context.timestamp,
            metrics={"outcomes_processed": len(outcomes)},
        ))
        return PhaseResult(
            phase=Phase.LEARN, passed=True,
            findings=findings, duration_ms=0.0,
        )
