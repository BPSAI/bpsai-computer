"""LEARN hook: captures tick observations as IdeaStore entries.

Reads observations, signal_ids, and hypothesis_ids from state_snapshot.
Each observation becomes an Idea with source="computer".
Idempotent: tracks tick_number to avoid duplicate recording.
"""

from __future__ import annotations

from engine.idea_store import IdeaStore
from engine.orchestration.learn.learn_event import LearnEvent, emit_learn_event
from engine.orchestration.models import Phase, PhaseResult, TickContext


MAX_BODY_LEN = 4096


class IdeaRecorder:
    """Captures tick observations as ideas."""

    def __init__(self, idea_store: IdeaStore) -> None:
        self._store = idea_store
        self._recorded_ticks: set[int] = set()

    @property
    def phase(self) -> Phase:
        return Phase.LEARN

    @property
    def priority(self) -> int:
        return 40

    async def execute(self, context: TickContext) -> PhaseResult:
        """Create ideas from tick observations."""
        if context.tick_number in self._recorded_ticks:
            emit_learn_event(context, LearnEvent(
                hook="IdeaRecorder",
                tick=context.tick_number,
                timestamp=context.timestamp,
                metrics={"skipped_duplicate_tick": True, "ideas_recorded": 0},
            ))
            return PhaseResult(
                phase=Phase.LEARN, passed=True,
                findings=[], duration_ms=0.0,
            )
        self._recorded_ticks.add(context.tick_number)

        observations = context.state_snapshot.get("observations", [])
        signal_ids = context.state_snapshot.get("signal_ids", [])
        hypothesis_ids = context.state_snapshot.get("hypothesis_ids", [])

        for obs in observations:
            body = obs[:MAX_BODY_LEN] if len(obs) > MAX_BODY_LEN else obs
            idea = self._store.add(
                body=body,
                tags=["learn-hook", "auto-captured"],
                source="computer",
                created_by="idea_recorder",
            )
            for sid in signal_ids:
                self._store.link_signal(idea.id, sid)
            if hypothesis_ids:
                self._store.link_hypothesis(idea.id, hypothesis_ids[0])

        emit_learn_event(context, LearnEvent(
            hook="IdeaRecorder",
            tick=context.tick_number,
            timestamp=context.timestamp,
            metrics={"ideas_recorded": len(observations)},
        ))
        return PhaseResult(
            phase=Phase.LEARN, passed=True, findings=[], duration_ms=0.0,
        )
