"""Auto-update docs/portfolio/status.yaml after sprint completion.

Reads the portfolio status file, applies sprint-completion changes
(test count, sprint status, shipped items), and writes back.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class SprintCompletion:
    """Describes a completed sprint for a single repo."""

    repo_key: str
    sprint_name: str
    test_count: int
    shipped_items: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo_key": self.repo_key,
            "sprint_name": self.sprint_name,
            "test_count": self.test_count,
            "shipped_items": list(self.shipped_items),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SprintCompletion:
        return cls(
            repo_key=data["repo_key"],
            sprint_name=data["sprint_name"],
            test_count=int(data["test_count"]),
            shipped_items=data.get("shipped_items", []),
        )


@dataclass
class StatusUpdateResult:
    """Outcome of a status update attempt."""

    success: bool
    repo_key: str
    changes: list[str] = field(default_factory=list)
    error: str | None = None


class StatusUpdater:
    """Reads, updates, and writes docs/portfolio/status.yaml."""

    def __init__(self, portfolio_dir: Path) -> None:
        self._dir = Path(portfolio_dir).resolve()
        self._path = self._dir / "status.yaml"
        self._data: dict[str, Any] | None = None

    def load(self) -> dict[str, Any] | None:
        """Load status.yaml. Returns None if missing or malformed."""
        if not self._path.exists():
            return None
        try:
            self._data = yaml.safe_load(self._path.read_text())
            return self._data
        except yaml.YAMLError:
            return None

    def save(self) -> None:
        """Write current state back to status.yaml."""
        if self._data is None:
            return
        self._path.write_text(yaml.dump(self._data, default_flow_style=False))

    def apply(self, completion: SprintCompletion) -> StatusUpdateResult:
        """Apply sprint completion to in-memory data. Does not write."""
        if self._data is None:
            self._data = self.load()
        if self._data is None:
            return StatusUpdateResult(
                success=False,
                repo_key=completion.repo_key,
                error="Could not load status.yaml",
            )

        repos = self._data.get("repos", {})
        if completion.repo_key not in repos:
            return StatusUpdateResult(
                success=False,
                repo_key=completion.repo_key,
                error=f"Repo key '{completion.repo_key}' not found in status.yaml",
            )

        repo = repos[completion.repo_key]
        changes: list[str] = []

        # Update sprint name
        old_sprint = repo.get("latest_sprint")
        if old_sprint != completion.sprint_name:
            repo["latest_sprint"] = completion.sprint_name
            changes.append(
                f"latest_sprint: {old_sprint} -> {completion.sprint_name}"
            )

        # Update sprint status
        old_status = repo.get("sprint_status")
        if old_status != "complete":
            repo["sprint_status"] = "complete"
            changes.append(f"sprint_status: {old_status} -> complete")

        # Update test count
        old_tests = repo.get("tests")
        if old_tests != completion.test_count:
            repo["tests"] = completion.test_count
            changes.append(f"tests: {old_tests} -> {completion.test_count}")

        # Update shipped items
        if completion.shipped_items:
            repo["shipped"] = list(completion.shipped_items)
            changes.append(f"shipped: {len(completion.shipped_items)} items")

        return StatusUpdateResult(
            success=True,
            repo_key=completion.repo_key,
            changes=changes,
        )

    def complete_sprint(self, completion: SprintCompletion) -> StatusUpdateResult:
        """Load, apply, and save in one call. Does not save on failure."""
        self.load()
        result = self.apply(completion)
        if result.success and result.changes:
            self.save()
        return result

    @staticmethod
    def count_tests(repo_path: Path) -> int:
        """Count test functions (def test_*) in a repo's tests/ directory."""
        repo_root = Path(repo_path).resolve()
        tests_dir = repo_root / "tests"
        if not tests_dir.exists():
            return 0
        count = 0
        pattern = re.compile(r"^\s*def (test_\w+)\s*\(", re.MULTILINE)
        for test_file in tests_dir.rglob("test_*.py"):
            if not test_file.resolve().is_relative_to(repo_root):
                continue
            try:
                content = test_file.read_text()
            except (OSError, UnicodeDecodeError):
                continue
            count += len(pattern.findall(content))
        return count
