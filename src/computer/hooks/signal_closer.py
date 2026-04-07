"""LEARN hook: closes signals whose linked tasks are complete."""

from __future__ import annotations

from bpsai_agent_core.hook_protocols import SignalStoreProtocol
from bpsai_agent_core.learn_event import LearnEvent, emit_learn_event
from bpsai_agent_core.tick import Phase, PhaseResult, TickContext


class SignalCloser:
    """Closes signals addressed by completed tasks."""

    def __init__(self, signal_store: SignalStoreProtocol) -> None:
        self._store = signal_store

    @property
    def phase(self) -> Phase:
        return Phase.LEARN

    @property
    def priority(self) -> int:
        return 30

    async def execute(self, context: TickContext) -> PhaseResult:
        """Close signals matched by completed task IDs."""
        completed = set(context.state_snapshot.get("completed_tasks", []))
        closed = 0
        if completed:
            for signal in self._store.list_active():
                if signal.action in completed:
                    self._store.close(
                        signal.signal_id,
                        f"Task {signal.action} completed",
                    )
                    closed += 1

        emit_learn_event(context, LearnEvent(
            hook="SignalCloser",
            tick=context.tick_number,
            timestamp=context.timestamp,
            metrics={"signals_closed": closed},
        ))
        return PhaseResult(
            phase=Phase.LEARN, passed=True, findings=[], duration_ms=0.0,
        )
