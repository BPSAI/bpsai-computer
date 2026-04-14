"""Tests for BatchHealthGate — detects environment-level batch failures."""

from __future__ import annotations

from computer.orchestration.config import DispatchResult, DispatchStatus, EnforcementMode
from computer.orchestration.health_gate import (
    BatchHealthGate,
    HealthGateConfig,
    HealthGateResult,
)


def _make_result(success: bool) -> DispatchResult:
    """Create a minimal DispatchResult for testing."""
    return DispatchResult(
        success=success,
        output="ok" if success else "Command failed with code 1",
        enforcement=EnforcementMode.CONTAINED_AUTO,
        method="subprocess",
        status=DispatchStatus.COMPLETE if success else DispatchStatus.FAILED,
    )


# --- Cycle 1: Rapid failures trigger abort ---


def test_three_rapid_failures_triggers_abort() -> None:
    gate = BatchHealthGate()
    fail = _make_result(success=False)

    r1 = gate.record(fail, duration_seconds=2.0)
    assert not r1.should_abort

    r2 = gate.record(fail, duration_seconds=3.0)
    assert not r2.should_abort

    r3 = gate.record(fail, duration_seconds=1.5)
    assert r3.should_abort
    assert r3.consecutive_rapid_failures == 3
    assert "rapid" in r3.reason.lower() or "environment" in r3.reason.lower()


def test_two_rapid_failures_no_abort() -> None:
    gate = BatchHealthGate()
    fail = _make_result(success=False)

    r1 = gate.record(fail, duration_seconds=2.0)
    r2 = gate.record(fail, duration_seconds=3.0)
    assert not r1.should_abort
    assert not r2.should_abort
    assert r2.consecutive_rapid_failures == 2


# --- Cycle 2: Success resets counter ---


def test_success_resets_consecutive_failures() -> None:
    gate = BatchHealthGate()
    fail = _make_result(success=False)
    ok = _make_result(success=True)

    gate.record(fail, duration_seconds=2.0)
    gate.record(fail, duration_seconds=2.0)
    r_ok = gate.record(ok, duration_seconds=5.0)
    assert r_ok.consecutive_rapid_failures == 0

    # Two more rapid failures should NOT abort (counter was reset)
    r4 = gate.record(fail, duration_seconds=2.0)
    r5 = gate.record(fail, duration_seconds=2.0)
    assert not r4.should_abort
    assert not r5.should_abort


# --- Cycle 3: Slow failure does not trigger gate ---


def test_slow_failure_resets_counter() -> None:
    gate = BatchHealthGate()
    fail = _make_result(success=False)

    gate.record(fail, duration_seconds=2.0)
    gate.record(fail, duration_seconds=2.0)

    # Slow failure — real code issue, not environment
    r_slow = gate.record(fail, duration_seconds=30.0)
    assert not r_slow.should_abort
    assert r_slow.consecutive_rapid_failures == 0


def test_slow_failure_between_rapid_prevents_abort() -> None:
    gate = BatchHealthGate()
    fail = _make_result(success=False)

    gate.record(fail, duration_seconds=2.0)  # rapid #1
    gate.record(fail, duration_seconds=25.0)  # slow -> resets
    r3 = gate.record(fail, duration_seconds=2.0)  # rapid #1 again
    assert not r3.should_abort
    assert r3.consecutive_rapid_failures == 1


# --- Cycle 4: Custom config, reset, mixed sequences ---


def test_custom_config_thresholds() -> None:
    config = HealthGateConfig(
        max_rapid_failures=2,
        rapid_threshold_seconds=5.0,
    )
    gate = BatchHealthGate(config=config)
    fail = _make_result(success=False)

    r1 = gate.record(fail, duration_seconds=3.0)
    assert not r1.should_abort

    r2 = gate.record(fail, duration_seconds=4.0)
    assert r2.should_abort
    assert r2.consecutive_rapid_failures == 2


def test_reset_clears_state() -> None:
    gate = BatchHealthGate()
    fail = _make_result(success=False)

    gate.record(fail, duration_seconds=2.0)
    gate.record(fail, duration_seconds=2.0)
    gate.reset()

    r3 = gate.record(fail, duration_seconds=2.0)
    assert not r3.should_abort
    assert r3.consecutive_rapid_failures == 1
    assert r3.tasks_completed == 1


def test_tasks_completed_and_remaining_tracking() -> None:
    config = HealthGateConfig(max_rapid_failures=5)
    gate = BatchHealthGate(config=config, total_tasks=10)
    fail = _make_result(success=False)
    ok = _make_result(success=True)

    r1 = gate.record(ok, duration_seconds=30.0)
    assert r1.tasks_completed == 1
    assert r1.tasks_remaining == 9

    r2 = gate.record(fail, duration_seconds=2.0)
    assert r2.tasks_completed == 2
    assert r2.tasks_remaining == 8


def test_min_tasks_before_gate_respected() -> None:
    config = HealthGateConfig(
        max_rapid_failures=1,
        min_tasks_before_gate=2,
    )
    gate = BatchHealthGate(config=config)
    fail = _make_result(success=False)

    # First task is rapid failure, but min_tasks_before_gate=2
    r1 = gate.record(fail, duration_seconds=1.0)
    assert not r1.should_abort

    # Second task is rapid failure, now gate kicks in
    r2 = gate.record(fail, duration_seconds=1.0)
    assert r2.should_abort


def test_default_health_gate_result_fields() -> None:
    gate = BatchHealthGate()
    ok = _make_result(success=True)

    r = gate.record(ok, duration_seconds=10.0)
    assert isinstance(r, HealthGateResult)
    assert r.should_abort is False
    assert r.reason == ""
    assert r.consecutive_rapid_failures == 0
    assert r.tasks_completed == 1
