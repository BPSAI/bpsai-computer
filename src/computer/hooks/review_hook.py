"""ENFORCE hook: reviews completed dispatches.

Detects completed dispatches in state_snapshot and spawns review
via the DispatchOrchestrator. Idempotent: tracks processed ticks.
"""

from __future__ import annotations

from computer.orchestration.config import (
    DispatchResult,
    DispatchStatus,
    EnforcementMode,
)
from computer.orchestration.orchestrator import DispatchOrchestrator
from engine.orchestration.models import Phase, PhaseResult, TickContext


class ReviewHook:
    """Detects completed dispatches and spawns review agents."""

    def __init__(self, orchestrator: DispatchOrchestrator) -> None:
        self._orchestrator = orchestrator
        self._processed_ticks: set[int] = set()

    @property
    def phase(self) -> Phase:
        return Phase.ENFORCE

    @property
    def priority(self) -> int:
        return 10

    async def execute(self, context: TickContext) -> PhaseResult:
        if context.tick_number in self._processed_ticks:
            return PhaseResult(
                phase=Phase.ENFORCE, passed=True,
                findings=[], duration_ms=0.0,
            )
        self._processed_ticks.add(context.tick_number)

        dispatches = context.state_snapshot.get("completed_dispatches", [])
        if not dispatches:
            return PhaseResult(
                phase=Phase.ENFORCE, passed=True,
                findings=[], duration_ms=0.0,
            )

        findings: list[str] = []
        for d in dispatches:
            result = _result_from_dict(d)
            review = self._orchestrator.review(result)
            status = "passed" if review.passed else "failed"
            findings.append(
                f"Review {d.get('session_id', '?')}: {status}"
            )

        return PhaseResult(
            phase=Phase.ENFORCE, passed=True,
            findings=findings, duration_ms=0.0,
        )


def _result_from_dict(data: dict) -> DispatchResult:
    """Reconstruct DispatchResult from dict."""
    status_val = data.get("status")
    status = DispatchStatus(status_val) if status_val else None
    enforcement_val = data.get("enforcement", "contained-auto")
    return DispatchResult(
        success=data.get("success", False),
        output=data.get("output", ""),
        enforcement=EnforcementMode(enforcement_val),
        method=data.get("method", "subprocess"),
        status=status,
        session_id=data.get("session_id"),
    )
