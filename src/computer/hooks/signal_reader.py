"""SENSE hook that reads active signals from a SignalStore into tick context."""

from __future__ import annotations

from bpsai_agent_core.hook_protocols import SignalStoreProtocol
from bpsai_agent_core.sense_event import SenseEvent, emit_sense_event
from bpsai_agent_core.tick import Phase, PhaseResult, TickContext


class SignalStoreReader:
    """Reads active signals from SignalStore and populates state_snapshot.

    Adds ``context.state_snapshot["signals"]`` as a list of signal dicts.
    """

    def __init__(self, signal_store: SignalStoreProtocol) -> None:
        self._store = signal_store

    @property
    def phase(self) -> Phase:
        return Phase.SENSE

    @property
    def priority(self) -> int:
        return 10

    async def execute(self, context: TickContext) -> PhaseResult:
        """Read active signals and inject into context."""
        active = self._store.list_active()
        context.state_snapshot["signals"] = [s.to_dict() for s in active]
        emit_sense_event(context, SenseEvent(
            hook="SignalStoreReader",
            tick=context.tick_number,
            timestamp=context.timestamp,
            metrics={"active_count": len(active)},
        ))
        return PhaseResult(
            phase=Phase.SENSE,
            passed=True,
            findings=[f"Read {len(active)} active signal(s)"],
            duration_ms=0.0,
        )
