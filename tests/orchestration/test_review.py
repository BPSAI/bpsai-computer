"""Tests for PR Review Automation — BP4.

Covers: ReviewResult model, Finding/Severity types, ReviewDispatcher
(parallel reviewer + security-auditor dispatch), findings collection,
and fix loop trigger back to Driver.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from engine.dispatch import Dispatcher
from engine.dispatch.config import DispatchResult, EnforcementMode
from computer.review.automation import (
    Finding,
    ReviewDispatcher,
    ReviewResult,
    Severity,
)
from computer.planning.types import SprintBacklog, SprintTask


# ---------- Helpers ----------


def _sample_backlog() -> SprintBacklog:
    return SprintBacklog(
        sprint_id="Bot-S35",
        repo="paircoder_bot",
        theme="Test Sprint",
        goal="Test goal",
        tasks=[
            SprintTask("T35.1", "Task A", "Desc A", 10, "P0"),
            SprintTask("T35.2", "Task B", "Desc B", 15, "P1"),
        ],
        status="approved",
    )


def _dispatch_ok(output: str = "No issues found.") -> DispatchResult:
    return DispatchResult(
        success=True, output=output,
        enforcement=EnforcementMode.CONTAINED_AUTO,
        method="subprocess",
    )


def _dispatch_fail(output: str = "Agent crashed") -> DispatchResult:
    return DispatchResult(
        success=False, output=output,
        enforcement=EnforcementMode.CONTAINED_AUTO,
        method="subprocess",
    )


# ---------- Severity ----------


class TestSeverity:
    def test_ordering(self):
        assert Severity.CRITICAL.value < Severity.HIGH.value
        assert Severity.HIGH.value < Severity.MEDIUM.value
        assert Severity.MEDIUM.value < Severity.LOW.value
        assert Severity.LOW.value < Severity.INFO.value

    def test_needs_fix_threshold(self):
        assert Severity.CRITICAL.needs_fix is True
        assert Severity.HIGH.needs_fix is True
        assert Severity.MEDIUM.needs_fix is False
        assert Severity.LOW.needs_fix is False
        assert Severity.INFO.needs_fix is False


# ---------- Finding ----------


class TestFinding:
    def test_construction(self):
        f = Finding(
            severity=Severity.HIGH,
            category="security",
            message="SQL injection in query builder",
            file_path="src/db.py",
            line=42,
            agent="security-auditor",
        )
        assert f.severity == Severity.HIGH
        assert f.agent == "security-auditor"
        assert f.line == 42

    def test_to_dict(self):
        f = Finding(
            severity=Severity.MEDIUM,
            category="quality",
            message="Function too long",
            file_path="src/handler.py",
            agent="reviewer",
        )
        d = f.to_dict()
        assert d["severity"] == "medium"
        assert d["category"] == "quality"
        assert d["agent"] == "reviewer"
        assert d["line"] is None

    def test_from_dict(self):
        d = {
            "severity": "high",
            "category": "security",
            "message": "Hardcoded secret",
            "file_path": "config.py",
            "line": 10,
            "agent": "security-auditor",
        }
        f = Finding.from_dict(d)
        assert f.severity == Severity.HIGH
        assert f.line == 10


# ---------- ReviewResult ----------


class TestReviewResult:
    def test_empty_result(self):
        r = ReviewResult(
            findings=[],
            reviewer_dispatched=True,
            auditor_dispatched=True,
        )
        assert r.needs_fix is False
        assert r.total_findings == 0

    def test_needs_fix_with_critical(self):
        r = ReviewResult(
            findings=[
                Finding(Severity.CRITICAL, "security", "RCE", "a.py", agent="security-auditor"),
            ],
            reviewer_dispatched=True,
            auditor_dispatched=True,
        )
        assert r.needs_fix is True

    def test_needs_fix_with_high(self):
        r = ReviewResult(
            findings=[
                Finding(Severity.HIGH, "quality", "Missing tests", "b.py", agent="reviewer"),
            ],
            reviewer_dispatched=True,
            auditor_dispatched=True,
        )
        assert r.needs_fix is True

    def test_no_fix_for_medium_only(self):
        r = ReviewResult(
            findings=[
                Finding(Severity.MEDIUM, "style", "Long function", "c.py", agent="reviewer"),
            ],
            reviewer_dispatched=True,
            auditor_dispatched=True,
        )
        assert r.needs_fix is False

    def test_total_findings(self):
        r = ReviewResult(
            findings=[
                Finding(Severity.LOW, "style", "Naming", "a.py", agent="reviewer"),
                Finding(Severity.HIGH, "security", "XSS", "b.py", agent="security-auditor"),
            ],
            reviewer_dispatched=True,
            auditor_dispatched=True,
        )
        assert r.total_findings == 2

    def test_to_dict(self):
        r = ReviewResult(
            findings=[
                Finding(Severity.HIGH, "quality", "Bug", "x.py", agent="reviewer"),
            ],
            reviewer_dispatched=True,
            auditor_dispatched=True,
            fix_dispatched=True,
        )
        d = r.to_dict()
        assert d["needs_fix"] is True
        assert d["total_findings"] == 1
        assert d["fix_dispatched"] is True
        assert len(d["findings"]) == 1

    def test_by_agent(self):
        findings = [
            Finding(Severity.HIGH, "quality", "Bug", "x.py", agent="reviewer"),
            Finding(Severity.LOW, "style", "Nit", "y.py", agent="reviewer"),
            Finding(Severity.CRITICAL, "sec", "RCE", "z.py", agent="security-auditor"),
        ]
        r = ReviewResult(
            findings=findings,
            reviewer_dispatched=True,
            auditor_dispatched=True,
        )
        by_agent = r.by_agent()
        assert len(by_agent["reviewer"]) == 2
        assert len(by_agent["security-auditor"]) == 1


# ---------- ReviewDispatcher ----------


class TestReviewDispatcher:
    def test_dispatches_reviewer_and_auditor(self, tmp_path):
        """Both reviewer and security-auditor dispatched."""
        dispatcher = MagicMock(spec=Dispatcher)
        dispatcher.dispatch.return_value = _dispatch_ok()

        rd = ReviewDispatcher(dispatcher)
        result = rd.review(tmp_path, _sample_backlog())

        assert result.reviewer_dispatched is True
        assert result.auditor_dispatched is True
        # At least 2 dispatch calls (reviewer + auditor)
        assert dispatcher.dispatch.call_count >= 2

    def test_reviewer_prompt_contains_review(self, tmp_path):
        """Reviewer dispatch prompt references review."""
        dispatcher = MagicMock(spec=Dispatcher)
        dispatcher.dispatch.return_value = _dispatch_ok()

        rd = ReviewDispatcher(dispatcher)
        rd.review(tmp_path, _sample_backlog())

        calls = dispatcher.dispatch.call_args_list
        prompts = [str(c) for c in calls]
        assert any("review" in p.lower() for p in prompts)

    def test_auditor_prompt_contains_security(self, tmp_path):
        """Security-auditor dispatch prompt references security."""
        dispatcher = MagicMock(spec=Dispatcher)
        dispatcher.dispatch.return_value = _dispatch_ok()

        rd = ReviewDispatcher(dispatcher)
        rd.review(tmp_path, _sample_backlog())

        calls = dispatcher.dispatch.call_args_list
        prompts = [str(c) for c in calls]
        assert any("security" in p.lower() for p in prompts)

    def test_collects_findings_from_output(self, tmp_path):
        """Findings parsed from dispatch output."""
        reviewer_output = (
            '{"findings": ['
            '{"severity": "high", "category": "quality", '
            '"message": "Missing error handling", '
            '"file_path": "src/api.py", "line": 55, "agent": "reviewer"}'
            "]}"
        )
        auditor_output = (
            '{"findings": ['
            '{"severity": "critical", "category": "security", '
            '"message": "SQL injection", '
            '"file_path": "src/db.py", "line": 12, "agent": "security-auditor"}'
            "]}"
        )
        dispatcher = MagicMock(spec=Dispatcher)
        dispatcher.dispatch.side_effect = [
            _dispatch_ok(reviewer_output),
            _dispatch_ok(auditor_output),
        ]

        rd = ReviewDispatcher(dispatcher)
        result = rd.review(tmp_path, _sample_backlog())

        assert result.total_findings == 2
        assert result.needs_fix is True

    def test_handles_non_json_output_gracefully(self, tmp_path):
        """Non-JSON output produces zero findings, not crash."""
        dispatcher = MagicMock(spec=Dispatcher)
        dispatcher.dispatch.return_value = _dispatch_ok("All good, no issues!")

        rd = ReviewDispatcher(dispatcher)
        result = rd.review(tmp_path, _sample_backlog())

        assert result.total_findings == 0
        assert result.needs_fix is False

    def test_handles_dispatch_failure(self, tmp_path):
        """Failed dispatch still returns result with dispatched=False."""
        dispatcher = MagicMock(spec=Dispatcher)
        dispatcher.dispatch.side_effect = [
            _dispatch_fail(),  # reviewer fails
            _dispatch_ok(),    # auditor succeeds
        ]

        rd = ReviewDispatcher(dispatcher)
        result = rd.review(tmp_path, _sample_backlog())

        assert result.reviewer_dispatched is False
        assert result.auditor_dispatched is True

    def test_handles_dispatch_exception(self, tmp_path):
        """Exception during dispatch caught gracefully."""
        dispatcher = MagicMock(spec=Dispatcher)
        dispatcher.dispatch.side_effect = [
            RuntimeError("Connection failed"),
            _dispatch_ok(),
        ]

        rd = ReviewDispatcher(dispatcher)
        result = rd.review(tmp_path, _sample_backlog())

        assert result.reviewer_dispatched is False
        assert result.auditor_dispatched is True

    def test_fix_loop_dispatches_driver(self, tmp_path):
        """When findings need fix, Driver dispatched for remediation."""
        reviewer_output = (
            '{"findings": ['
            '{"severity": "high", "category": "quality", '
            '"message": "Missing tests for auth module", '
            '"file_path": "src/auth.py", "line": 30, "agent": "reviewer"}'
            "]}"
        )
        dispatcher = MagicMock(spec=Dispatcher)
        dispatcher.dispatch.side_effect = [
            _dispatch_ok(reviewer_output),  # reviewer
            _dispatch_ok(),                  # auditor
            _dispatch_ok(),                  # fix driver
        ]

        rd = ReviewDispatcher(dispatcher)
        result = rd.review(tmp_path, _sample_backlog())

        assert result.needs_fix is True
        assert result.fix_dispatched is True
        # 3 calls: reviewer + auditor + driver fix
        assert dispatcher.dispatch.call_count == 3

    def test_fix_loop_prompt_includes_findings(self, tmp_path):
        """Fix driver prompt includes the findings to address."""
        reviewer_output = (
            '{"findings": ['
            '{"severity": "high", "category": "quality", '
            '"message": "Missing error handling", '
            '"file_path": "src/api.py", "line": 55, "agent": "reviewer"}'
            "]}"
        )
        dispatcher = MagicMock(spec=Dispatcher)
        dispatcher.dispatch.side_effect = [
            _dispatch_ok(reviewer_output),
            _dispatch_ok(),
            _dispatch_ok(),  # fix
        ]

        rd = ReviewDispatcher(dispatcher)
        rd.review(tmp_path, _sample_backlog())

        fix_call = dispatcher.dispatch.call_args_list[2]
        fix_prompt = str(fix_call)
        assert "missing error handling" in fix_prompt.lower()

    def test_no_fix_loop_when_no_critical_findings(self, tmp_path):
        """No Driver dispatch when only low/medium findings."""
        reviewer_output = (
            '{"findings": ['
            '{"severity": "low", "category": "style", '
            '"message": "Naming convention", '
            '"file_path": "src/util.py", "line": 10, "agent": "reviewer"}'
            "]}"
        )
        dispatcher = MagicMock(spec=Dispatcher)
        dispatcher.dispatch.side_effect = [
            _dispatch_ok(reviewer_output),
            _dispatch_ok(),
        ]

        rd = ReviewDispatcher(dispatcher)
        result = rd.review(tmp_path, _sample_backlog())

        assert result.needs_fix is False
        assert result.fix_dispatched is False
        # Only 2 calls: reviewer + auditor, no fix
        assert dispatcher.dispatch.call_count == 2
