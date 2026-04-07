"""LEARN hook: draft next sprint backlog after sprint completion.

Reads completed_tasks, standup_items, and next_sprint config from
state_snapshot and stores the draft backlog. Idempotent: tracks ticks.

Note: The actual NextSprintAuthor business logic should be injected
via the author_factory parameter. This hook only orchestrates the call.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from bpsai_agent_core.learn_event import LearnEvent, emit_learn_event
from bpsai_agent_core.tick import Phase, PhaseResult, TickContext


@runtime_checkable
class SprintAuthorProtocol(Protocol):
    """Protocol for next sprint authoring."""

    def plan_next(
        self,
        completed_tasks: list[Any],
        standup_items: list[Any],
        target_repo: str,
        next_sprint_id: str,
        theme: str,
    ) -> Any: ...


def _emit_skip(context: TickContext, reason: str) -> PhaseResult:
    """Emit a skip event and return a passing PhaseResult."""
    emit_learn_event(context, LearnEvent(
        hook="NextSprintHook",
        tick=context.tick_number,
        timestamp=context.timestamp,
        metrics={reason: True, "tasks_drafted": 0},
    ))
    return PhaseResult(
        phase=Phase.LEARN, passed=True,
        findings=[], duration_ms=0.0,
    )


class NextSprintHook:
    """Drafts the next sprint backlog when completion data is available."""

    def __init__(
        self, author_factory: type | None = None,
    ) -> None:
        self._author_factory = author_factory
        self._processed_ticks: set[int] = set()

    @property
    def phase(self) -> Phase:
        return Phase.LEARN

    @property
    def priority(self) -> int:
        return 30

    async def execute(self, context: TickContext) -> PhaseResult:
        if context.tick_number in self._processed_ticks:
            return _emit_skip(context, "skipped_duplicate_tick")
        self._processed_ticks.add(context.tick_number)

        next_sprint_cfg = context.state_snapshot.get("next_sprint")
        if not next_sprint_cfg:
            return _emit_skip(context, "skipped_no_config")

        if self._author_factory is None:
            return _emit_skip(context, "skipped_no_author")

        completed = context.state_snapshot.get("completed_tasks", [])
        standups = context.state_snapshot.get("standup_items", [])

        author = self._author_factory()
        draft = author.plan_next(
            completed_tasks=completed,
            standup_items=standups,
            target_repo=next_sprint_cfg["target_repo"],
            next_sprint_id=next_sprint_cfg["sprint_id"],
            theme=next_sprint_cfg.get("theme", "Follow-up"),
        )

        context.state_snapshot["next_sprint_draft"] = (
            draft.to_dict() if hasattr(draft, "to_dict") else draft
        )

        emit_learn_event(context, LearnEvent(
            hook="NextSprintHook",
            tick=context.tick_number,
            timestamp=context.timestamp,
            metrics={"tasks_drafted": 1},
        ))
        return PhaseResult(
            phase=Phase.LEARN, passed=True,
            findings=["Draft backlog produced"],
            duration_ms=0.0,
        )
