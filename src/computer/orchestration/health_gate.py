"""BatchHealthGate — detects environment-level batch failures.

Monitors dispatch results during headless batch execution and signals
when the batch should abort due to rapid sequential failures (indicating
an environment issue rather than individual task failures).

Usage in a batch loop::

    from computer.orchestration.health_gate import BatchHealthGate, HealthGateConfig
    import time

    gate = BatchHealthGate(total_tasks=len(tasks))

    for task in tasks:
        start = time.monotonic()
        result = dispatcher.dispatch(repo, task.prompt)
        elapsed = time.monotonic() - start

        check = gate.record(result, duration_seconds=elapsed)
        if check.should_abort:
            log.error("Aborting batch: %s", check.reason)
            break
"""

from __future__ import annotations

from dataclasses import dataclass

from computer.orchestration.config import DispatchResult


@dataclass(frozen=True)
class HealthGateConfig:
    """Tuning knobs for batch health detection."""

    max_rapid_failures: int = 3
    rapid_threshold_seconds: float = 10.0
    min_tasks_before_gate: int = 1


@dataclass(frozen=True)
class HealthGateResult:
    """Outcome of a single health gate check."""

    should_abort: bool
    reason: str
    consecutive_rapid_failures: int
    tasks_completed: int
    tasks_remaining: int


class BatchHealthGate:
    """Monitors dispatch results and aborts on environment-level failures.

    A "rapid failure" is one that completes in less than
    ``rapid_threshold_seconds`` — typical of environment issues (missing
    tool, bad auth) rather than real code failures which take longer.

    The gate triggers when ``max_rapid_failures`` consecutive rapid
    failures are recorded. A success or a slow failure resets the counter.
    """

    def __init__(
        self,
        config: HealthGateConfig | None = None,
        total_tasks: int = 0,
    ) -> None:
        self._config = config or HealthGateConfig()
        self._total_tasks = total_tasks
        self._consecutive_rapid: int = 0
        self._tasks_completed: int = 0

    def record(
        self, result: DispatchResult, duration_seconds: float,
    ) -> HealthGateResult:
        """Record a dispatch result and return a health assessment."""
        self._tasks_completed += 1
        self._update_counter(result, duration_seconds)
        return self._evaluate()

    def reset(self) -> None:
        """Clear all tracked state."""
        self._consecutive_rapid = 0
        self._tasks_completed = 0

    def _update_counter(
        self, result: DispatchResult, duration_seconds: float,
    ) -> None:
        """Update the consecutive rapid failure counter."""
        is_rapid = duration_seconds < self._config.rapid_threshold_seconds
        if not result.success and is_rapid:
            self._consecutive_rapid += 1
        else:
            self._consecutive_rapid = 0

    def _evaluate(self) -> HealthGateResult:
        """Build the gate result from current state."""
        remaining = max(0, self._total_tasks - self._tasks_completed)
        should_abort = (
            self._consecutive_rapid >= self._config.max_rapid_failures
            and self._tasks_completed >= self._config.min_tasks_before_gate
        )
        reason = ""
        if should_abort:
            reason = (
                f"Aborting: {self._consecutive_rapid} consecutive rapid "
                f"failures detected (environment issue likely)"
            )
        return HealthGateResult(
            should_abort=should_abort,
            reason=reason,
            consecutive_rapid_failures=self._consecutive_rapid,
            tasks_completed=self._tasks_completed,
            tasks_remaining=remaining,
        )
