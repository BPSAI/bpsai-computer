"""Contract tests for severity routing (T2I.6).

Validates:
- Severity enum values and ordering
- Threshold filtering logic (min_severity)
- Default severity for messages without one
- ChannelEnvelope severity field constraints
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from computer.contracts import ChannelEnvelope
from computer.contracts.messages import (
    SEVERITY_LEVELS,
    SEVERITY_ORDER,
    Severity,
    severities_at_or_above,
)


class TestSeverityEnum:
    """Severity enum has the four required levels."""

    def test_info_level(self):
        assert Severity.INFO == "info"

    def test_warning_level(self):
        assert Severity.WARNING == "warning"

    def test_error_level(self):
        assert Severity.ERROR == "error"

    def test_critical_level(self):
        assert Severity.CRITICAL == "critical"

    def test_exactly_four_levels(self):
        assert len(Severity) == 4

    def test_levels_constant_matches_enum(self):
        assert SEVERITY_LEVELS == {"info", "warning", "error", "critical"}


class TestSeverityOrdering:
    """Severity has a defined ordering: info < warning < error < critical."""

    def test_info_is_lowest(self):
        assert SEVERITY_ORDER["info"] == 0

    def test_warning_above_info(self):
        assert SEVERITY_ORDER["warning"] > SEVERITY_ORDER["info"]

    def test_error_above_warning(self):
        assert SEVERITY_ORDER["error"] > SEVERITY_ORDER["warning"]

    def test_critical_is_highest(self):
        assert SEVERITY_ORDER["critical"] > SEVERITY_ORDER["error"]

    def test_order_covers_all_levels(self):
        assert set(SEVERITY_ORDER.keys()) == SEVERITY_LEVELS


class TestSeveritiesAtOrAbove:
    """severities_at_or_above returns all levels >= the given threshold."""

    def test_min_info_returns_all(self):
        result = severities_at_or_above("info")
        assert result == {"info", "warning", "error", "critical"}

    def test_min_warning_excludes_info(self):
        result = severities_at_or_above("warning")
        assert result == {"warning", "error", "critical"}

    def test_min_error_excludes_info_and_warning(self):
        result = severities_at_or_above("error")
        assert result == {"error", "critical"}

    def test_min_critical_returns_only_critical(self):
        result = severities_at_or_above("critical")
        assert result == {"critical"}

    def test_invalid_severity_raises(self):
        with pytest.raises(ValueError, match="Unknown severity"):
            severities_at_or_above("debug")


class TestChannelEnvelopeSeverityDefault:
    """Messages without severity default to info."""

    def test_severity_defaults_to_info(self):
        env = ChannelEnvelope(
            type="dispatch",
            from_project="computer",
            to_project="bellona",
            content="test",
        )
        assert env.severity == "info"

    def test_explicit_severity_preserved(self):
        env = ChannelEnvelope(
            type="alert",
            from_project="computer",
            to_project="bellona",
            content="down",
            severity="critical",
        )
        assert env.severity == "critical"

    def test_invalid_severity_rejected(self):
        with pytest.raises(ValidationError, match="severity"):
            ChannelEnvelope(
                type="alert",
                from_project="computer",
                to_project="bellona",
                content="x",
                severity="debug",
            )
