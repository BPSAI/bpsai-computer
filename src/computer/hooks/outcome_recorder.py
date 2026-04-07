"""LEARN hook: records tick findings and actions to the DecisionJournal."""

from __future__ import annotations

from bpsai_agent_core.hook_protocols import DecisionJournalProtocol
from bpsai_agent_core.learn_event import LearnEvent, emit_learn_event
from bpsai_agent_core.tick import Phase, PhaseResult, TickContext

from computer.hooks.hook_types import CNSDecision, DecisionType


class OutcomeRecorder:
    """Logs tick outcomes to the DecisionJournal."""

    def __init__(self, journal: DecisionJournalProtocol) -> None:
        self._journal = journal
        self._recorded_ticks: set[int] = set()

    @property
    def phase(self) -> Phase:
        return Phase.LEARN

    @property
    def priority(self) -> int:
        return 10

    def _record_outcomes(self, context: TickContext) -> tuple[int, int]:
        """Record actions and deferred findings."""
        actions = context.state_snapshot.get("actions", [])
        findings = context.state_snapshot.get("findings", [])
        action_set = set(actions)

        for i, action in enumerate(actions):
            self._journal.record(CNSDecision(
                decision_id=f"tick-{context.tick_number}-dispatch-{i}",
                timestamp=context.timestamp,
                decision_type=DecisionType.DISPATCH,
                observation=action,
                diagnosis="auto-recorded from tick",
                prescription=action,
                expected_outcome="resolved",
            ))

        defer_count = 0
        for finding in findings:
            if finding not in action_set:
                self._journal.record(CNSDecision(
                    decision_id=f"tick-{context.tick_number}-defer-{defer_count}",
                    timestamp=context.timestamp,
                    decision_type=DecisionType.DEFER,
                    observation=finding,
                    diagnosis="auto-recorded from tick",
                    prescription="deferred",
                    expected_outcome="pending review",
                ))
                defer_count += 1

        return len(actions), defer_count

    async def execute(self, context: TickContext) -> PhaseResult:
        """Record findings/actions from previous tick phases."""
        if context.tick_number in self._recorded_ticks:
            emit_learn_event(context, LearnEvent(
                hook="OutcomeRecorder",
                tick=context.tick_number,
                timestamp=context.timestamp,
                metrics={
                    "skipped_duplicate_tick": True,
                    "dispatches_recorded": 0,
                    "deferrals_recorded": 0,
                },
            ))
            return PhaseResult(
                phase=Phase.LEARN, passed=True,
                findings=[], duration_ms=0.0,
            )
        self._recorded_ticks.add(context.tick_number)

        dispatches, deferrals = self._record_outcomes(context)

        emit_learn_event(context, LearnEvent(
            hook="OutcomeRecorder",
            tick=context.tick_number,
            timestamp=context.timestamp,
            metrics={
                "dispatches_recorded": dispatches,
                "deferrals_recorded": deferrals,
            },
        ))
        return PhaseResult(
            phase=Phase.LEARN, passed=True, findings=[], duration_ms=0.0,
        )
