"""IdeaObserverHook — SENSE phase hook that captures findings as ideas.

Reads findings from ``context.state_snapshot["findings"]`` (populated by
PatternDetectorHook) and stores each as an idea in IdeaStore via
``capture_from_agent()``.
"""

from __future__ import annotations

from engine.idea_capture import capture_from_agent
from engine.idea_store import IdeaStore
from engine.orchestration.models import Phase, PhaseResult, TickContext
from engine.orchestration.sense.sense_event import SenseEvent, emit_sense_event


MAX_BODY_LEN = 4096


def _filter_relevant_signals(
    finding: str,
    raw_signals: list,
) -> list[str]:
    """Return signal IDs relevant to *finding*.

    Heuristic: if a signal's hyp_link or signal_id appears in the finding
    text, it is relevant.  If a signal's category appears in the finding,
    it is relevant.  Falls back to all signals only when no match found.

    TODO: Replace with RelevanceScorer when wired in.
    """
    matched: list[str] = []
    finding_lower = finding.lower()
    for sig in raw_signals:
        sid = sig["signal_id"] if isinstance(sig, dict) else sig.signal_id
        cat = sig.get("category", "") if isinstance(sig, dict) else getattr(sig, "category", "")
        hyp = sig.get("hyp_link", "") if isinstance(sig, dict) else getattr(sig, "hyp_link", "")
        if sid.lower() in finding_lower:
            matched.append(sid)
        elif hyp and hyp.lower() in finding_lower:
            matched.append(sid)
        elif cat and cat.lower() in finding_lower:
            matched.append(sid)
    # No fallback: unmatched findings get no signal links.
    return matched


class IdeaObserverHook:
    """Capture pattern-detector findings as ideas in IdeaStore."""

    def __init__(self, idea_store: IdeaStore) -> None:
        self._store = idea_store
        self._recorded_ticks: set[int] = set()

    @property
    def phase(self) -> Phase:
        return Phase.SENSE

    @property
    def priority(self) -> int:
        return 50

    async def execute(self, context: TickContext) -> PhaseResult:
        """Capture each finding as an observed idea."""
        if context.tick_number in self._recorded_ticks:
            emit_sense_event(context, SenseEvent(
                hook="IdeaObserverHook",
                tick=context.tick_number,
                timestamp=context.timestamp,
                metrics={"ideas_captured": 0, "skipped_duplicate_tick": True},
            ))
            return PhaseResult(
                phase=Phase.SENSE, passed=True,
                findings=[], duration_ms=0.0,
            )
        self._recorded_ticks.add(context.tick_number)
        findings: list[str] = context.state_snapshot.get("findings", [])
        raw_signals = context.state_snapshot.get("signals", [])
        for finding in findings:
            body = finding[:MAX_BODY_LEN] if len(finding) > MAX_BODY_LEN else finding
            result = capture_from_agent(
                store=self._store,
                body=body,
                tags=["sense", "pattern_detection"],
                agent_id="pattern_detector",
                confidence=0.5,
            )
            # TODO: Replace heuristic with RelevanceScorer when wired in.
            relevant_ids = _filter_relevant_signals(
                finding, raw_signals,
            )
            for sid in relevant_ids:
                self._store.link_signal(result.idea.id, sid)
        emit_sense_event(context, SenseEvent(
            hook="IdeaObserverHook",
            tick=context.tick_number,
            timestamp=context.timestamp,
            metrics={
                "ideas_captured": len(findings),
                "skipped_duplicate_tick": False,
            },
        ))
        summary = (
            [f"IdeaObserver captured {len(findings)} findings"]
            if findings
            else []
        )
        return PhaseResult(
            phase=Phase.SENSE,
            passed=True,
            findings=summary,
            duration_ms=0.0,
        )
