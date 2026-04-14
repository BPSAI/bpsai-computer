"""PR Review Automation — dispatch reviewer + security-auditor, collect findings.

After a Navigator completes work, ReviewDispatcher launches reviewer and
security-auditor agents in parallel, collects structured findings, and
triggers a fix loop (Driver dispatch) when critical/high issues are found.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from engine.dispatch import Dispatcher
from engine.dispatch.config import DispatchResult
from computer.planning.types import SprintBacklog


class Severity(Enum):
    """Finding severity — lower value = more severe."""

    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    INFO = 5

    @property
    def needs_fix(self) -> bool:
        return self.value <= Severity.HIGH.value


@dataclass
class Finding:
    """A single review or audit finding."""

    severity: Severity
    category: str
    message: str
    file_path: str
    line: Optional[int] = None
    agent: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity.name.lower(),
            "category": self.category,
            "message": self.message,
            "file_path": self.file_path,
            "line": self.line,
            "agent": self.agent,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Finding:
        return cls(
            severity=Severity[data["severity"].upper()],
            category=data["category"],
            message=data["message"],
            file_path=data["file_path"],
            line=data.get("line"),
            agent=data.get("agent", ""),
        )


@dataclass
class ReviewResult:
    """Aggregated result of reviewer + security-auditor dispatch."""

    findings: list[Finding] = field(default_factory=list)
    reviewer_dispatched: bool = False
    auditor_dispatched: bool = False
    fix_dispatched: bool = False

    @property
    def needs_fix(self) -> bool:
        return any(f.severity.needs_fix for f in self.findings)

    @property
    def total_findings(self) -> int:
        return len(self.findings)

    def by_agent(self) -> dict[str, list[Finding]]:
        result: dict[str, list[Finding]] = {}
        for f in self.findings:
            result.setdefault(f.agent, []).append(f)
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "reviewer_dispatched": self.reviewer_dispatched,
            "auditor_dispatched": self.auditor_dispatched,
            "fix_dispatched": self.fix_dispatched,
            "needs_fix": self.needs_fix,
            "total_findings": self.total_findings,
        }


def _parse_findings(output: str) -> list[Finding]:
    """Parse structured findings from agent output."""
    try:
        data = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        return []
    raw = data.get("findings", [])
    findings: list[Finding] = []
    for item in raw:
        try:
            findings.append(Finding.from_dict(item))
        except (KeyError, ValueError):
            continue
    return findings


def _build_review_prompt(backlog: SprintBacklog) -> str:
    task_ids = ", ".join(t.task_id for t in backlog.tasks)
    return (
        f"Review changes from sprint {backlog.sprint_id} "
        f"({backlog.theme}). Check code quality, test coverage, "
        f"and acceptance criteria for tasks: {task_ids}."
    )


def _build_audit_prompt(backlog: SprintBacklog) -> str:
    task_ids = ", ".join(t.task_id for t in backlog.tasks)
    return (
        f"Security audit for sprint {backlog.sprint_id} "
        f"({backlog.theme}). Check for security vulnerabilities, "
        f"secrets exposure, and OWASP top 10 issues in tasks: "
        f"{task_ids}."
    )


def _build_fix_prompt(findings: list[Finding]) -> str:
    lines = ["Fix the following review findings:"]
    for f in findings:
        if f.severity.needs_fix:
            loc = f"{f.file_path}:{f.line}" if f.line else f.file_path
            lines.append(
                f"- [{f.severity.name}] {f.message} ({loc})"
            )
    return "\n".join(lines)


def _dispatch_agent(
    dispatcher: Dispatcher, repo_path: Path, prompt: str,
) -> tuple[bool, list[Finding]]:
    """Dispatch an agent and collect findings. Returns (success, findings)."""
    try:
        result = dispatcher.dispatch(repo_path, prompt)
    except Exception:
        return False, []
    if not result.success:
        return False, []
    return True, _parse_findings(result.output)


class ReviewDispatcher:
    """Dispatches reviewer + security-auditor and collects findings."""

    def __init__(self, dispatcher: Dispatcher) -> None:
        self._dispatcher = dispatcher

    def review(
        self, repo_path: Path, backlog: SprintBacklog,
    ) -> ReviewResult:
        """Run review + audit, trigger fix loop if needed."""
        repo_path = Path(repo_path)

        # Dispatch reviewer
        rev_ok, rev_findings = _dispatch_agent(
            self._dispatcher, repo_path,
            _build_review_prompt(backlog),
        )

        # Dispatch security-auditor
        aud_ok, aud_findings = _dispatch_agent(
            self._dispatcher, repo_path,
            _build_audit_prompt(backlog),
        )

        all_findings = rev_findings + aud_findings
        result = ReviewResult(
            findings=all_findings,
            reviewer_dispatched=rev_ok,
            auditor_dispatched=aud_ok,
        )

        # Fix loop: dispatch Driver if critical/high findings
        if result.needs_fix:
            fix_prompt = _build_fix_prompt(all_findings)
            try:
                fix_result = self._dispatcher.dispatch(
                    repo_path, fix_prompt,
                )
                result.fix_dispatched = fix_result.success
            except Exception:
                result.fix_dispatched = False

        return result
