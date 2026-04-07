"""LEARN hook: auto-update status.yaml after sprint completion.

Reads sprint_completion from state_snapshot and delegates to
a StatusUpdater protocol. Idempotent: tracks processed ticks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from bpsai_agent_core.learn_event import LearnEvent, emit_learn_event
from bpsai_agent_core.tick import Phase, PhaseResult, TickContext

from computer.hooks.hook_types import SprintCompletion


@runtime_checkable
class StatusUpdaterProtocol(Protocol):
    """Protocol for status.yaml updater."""

    def complete_sprint(self, completion: Any) -> Any: ...


def _emit_skip(context: TickContext, reason: str) -> PhaseResult:
    """Emit a skip event and return a passing PhaseResult."""
    emit_learn_event(context, LearnEvent(
        hook="StatusUpdateHook",
        tick=context.tick_number,
        timestamp=context.timestamp,
        metrics={reason: True, "changes": 0},
    ))
    return PhaseResult(
        phase=Phase.LEARN, passed=True,
        findings=[], duration_ms=0.0,
    )


class StatusUpdateHook:
    """Updates status.yaml when sprint completion data is present."""

    def __init__(
        self,
        portfolio_dir: Path,
        updater_factory: type | None = None,
    ) -> None:
        self._portfolio_dir = Path(portfolio_dir).resolve()
        self._updater_factory = updater_factory
        self._processed_ticks: set[int] = set()

    @property
    def phase(self) -> Phase:
        return Phase.LEARN

    @property
    def priority(self) -> int:
        return 25

    async def execute(self, context: TickContext) -> PhaseResult:
        if context.tick_number in self._processed_ticks:
            return _emit_skip(context, "skipped_duplicate_tick")
        self._processed_ticks.add(context.tick_number)

        completion_data = context.state_snapshot.get("sprint_completion")
        if not completion_data:
            return _emit_skip(context, "skipped_no_completion")

        if self._updater_factory is None:
            return _emit_skip(context, "skipped_no_updater")

        completion = SprintCompletion.from_dict(completion_data)
        updater = self._updater_factory(self._portfolio_dir)
        result = updater.complete_sprint(completion)

        findings: list[str] = []
        if result.success:
            findings.extend(result.changes)
        else:
            findings.append(f"Status update failed: {result.error}")

        emit_learn_event(context, LearnEvent(
            hook="StatusUpdateHook",
            tick=context.tick_number,
            timestamp=context.timestamp,
            metrics={
                "success": result.success,
                "changes": len(result.changes),
                "repo_key": completion.repo_key,
            },
        ))
        return PhaseResult(
            phase=Phase.LEARN, passed=True,
            findings=findings, duration_ms=0.0,
        )
