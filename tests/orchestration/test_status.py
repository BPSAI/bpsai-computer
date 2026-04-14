"""Tests for engine.status_updater — status.yaml auto-update after sprint completion."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from computer.status.updater import (
    SprintCompletion,
    StatusUpdater,
    StatusUpdateResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_STATUS = {
    "repos": {
        "bpsai-framework": {
            "shortcode": "FW",
            "latest_sprint": "G2",
            "sprint_status": "in_progress",
            "tests": 1308,
            "branch": "main",
        },
        "paircoder": {
            "shortcode": "CLI",
            "latest_sprint": "G2",
            "sprint_status": "complete",
            "tests": 9900,
            "branch": "main",
        },
    },
}


@pytest.fixture
def status_dir(tmp_path: Path) -> Path:
    """Create a temp portfolio dir with a status.yaml."""
    (tmp_path / "status.yaml").write_text(yaml.safe_dump(MINIMAL_STATUS))
    return tmp_path


@pytest.fixture
def updater(status_dir: Path) -> StatusUpdater:
    return StatusUpdater(status_dir)


# ---------------------------------------------------------------------------
# SprintCompletion model tests
# ---------------------------------------------------------------------------


class TestSprintCompletion:
    def test_minimal_creation(self) -> None:
        sc = SprintCompletion(
            repo_key="bpsai-framework",
            sprint_name="G3",
            test_count=1423,
        )
        assert sc.repo_key == "bpsai-framework"
        assert sc.sprint_name == "G3"
        assert sc.test_count == 1423
        assert sc.shipped_items == []

    def test_with_shipped_items(self) -> None:
        sc = SprintCompletion(
            repo_key="paircoder",
            sprint_name="CLI-S43",
            test_count=10000,
            shipped_items=["Dynamic thresholds", "Fail-closed gate"],
        )
        assert len(sc.shipped_items) == 2

    def test_to_dict(self) -> None:
        sc = SprintCompletion(
            repo_key="paircoder",
            sprint_name="CLI-S43",
            test_count=10000,
            shipped_items=["Item A"],
        )
        d = sc.to_dict()
        assert d["repo_key"] == "paircoder"
        assert d["sprint_name"] == "CLI-S43"
        assert d["test_count"] == 10000
        assert d["shipped_items"] == ["Item A"]

    def test_from_dict(self) -> None:
        raw = {
            "repo_key": "paircoder_bot",
            "sprint_name": "Bot-S34",
            "test_count": 2724,
            "shipped_items": ["Metis closes the loop"],
        }
        sc = SprintCompletion.from_dict(raw)
        assert sc.repo_key == "paircoder_bot"
        assert sc.sprint_name == "Bot-S34"
        assert sc.test_count == 2724
        assert sc.shipped_items == ["Metis closes the loop"]


# ---------------------------------------------------------------------------
# StatusUpdateResult model tests
# ---------------------------------------------------------------------------


class TestStatusUpdateResult:
    def test_success_result(self) -> None:
        r = StatusUpdateResult(
            success=True,
            repo_key="bpsai-framework",
            changes=["sprint_status: in_progress -> complete", "tests: 1308 -> 1423"],
        )
        assert r.success is True
        assert len(r.changes) == 2
        assert r.error is None

    def test_failure_result(self) -> None:
        r = StatusUpdateResult(
            success=False,
            repo_key="bpsai-framework",
            changes=[],
            error="Repo key not found in status.yaml",
        )
        assert r.success is False
        assert r.error == "Repo key not found in status.yaml"


# ---------------------------------------------------------------------------
# StatusUpdater — reading & updating
# ---------------------------------------------------------------------------


class TestStatusUpdaterLoad:
    def test_loads_status_yaml(self, updater: StatusUpdater) -> None:
        data = updater.load()
        assert "repos" in data
        assert "bpsai-framework" in data["repos"]

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        u = StatusUpdater(tmp_path)
        assert u.load() is None

    def test_malformed_yaml_returns_none(self, tmp_path: Path) -> None:
        (tmp_path / "status.yaml").write_text(": bad: yaml: [[[")
        u = StatusUpdater(tmp_path)
        assert u.load() is None

    def test_empty_file_returns_none(self, tmp_path: Path) -> None:
        (tmp_path / "status.yaml").write_text("")
        u = StatusUpdater(tmp_path)
        assert u.load() is None


class TestStatusUpdaterApply:
    def test_updates_sprint_status(
        self, updater: StatusUpdater, status_dir: Path
    ) -> None:
        completion = SprintCompletion(
            repo_key="bpsai-framework",
            sprint_name="G3",
            test_count=1423,
        )
        result = updater.apply(completion)
        assert result.success is True
        assert any("sprint_status" in c for c in result.changes)

        # Save and re-read to verify persistence
        updater.save()
        data = StatusUpdater(status_dir).load()
        repo = data["repos"]["bpsai-framework"]
        assert repo["sprint_status"] == "complete"
        assert repo["latest_sprint"] == "G3"

    def test_updates_test_count(
        self, updater: StatusUpdater, status_dir: Path
    ) -> None:
        completion = SprintCompletion(
            repo_key="bpsai-framework",
            sprint_name="G3",
            test_count=1500,
        )
        result = updater.apply(completion)
        assert result.success is True
        assert any("tests" in c for c in result.changes)

        updater.save()
        data = StatusUpdater(status_dir).load()
        assert data["repos"]["bpsai-framework"]["tests"] == 1500

    def test_updates_shipped_items(
        self, updater: StatusUpdater, status_dir: Path
    ) -> None:
        completion = SprintCompletion(
            repo_key="bpsai-framework",
            sprint_name="G3",
            test_count=1423,
            shipped_items=["Dispatch engine", "Review automation"],
        )
        result = updater.apply(completion)
        assert result.success is True

        updater.save()
        data = StatusUpdater(status_dir).load()
        repo = data["repos"]["bpsai-framework"]
        assert repo.get("shipped") == ["Dispatch engine", "Review automation"]

    def test_unknown_repo_fails(self, updater: StatusUpdater) -> None:
        completion = SprintCompletion(
            repo_key="nonexistent-repo",
            sprint_name="S1",
            test_count=100,
        )
        result = updater.apply(completion)
        assert result.success is False
        assert "not found" in result.error.lower()

    def test_no_status_file_fails(self, tmp_path: Path) -> None:
        u = StatusUpdater(tmp_path)
        completion = SprintCompletion(
            repo_key="bpsai-framework",
            sprint_name="G3",
            test_count=1423,
        )
        result = u.apply(completion)
        assert result.success is False

    def test_no_change_when_values_same(self, status_dir: Path) -> None:
        u = StatusUpdater(status_dir)
        completion = SprintCompletion(
            repo_key="paircoder",
            sprint_name="G2",
            test_count=9900,
        )
        result = u.apply(completion)
        assert result.success is True
        assert len(result.changes) == 0


# ---------------------------------------------------------------------------
# StatusUpdater — YAML round-trip (write + re-read)
# ---------------------------------------------------------------------------


class TestYamlRoundTrip:
    def test_save_and_reload(self, updater: StatusUpdater, status_dir: Path) -> None:
        completion = SprintCompletion(
            repo_key="bpsai-framework",
            sprint_name="G3",
            test_count=1500,
            shipped_items=["Feature A"],
        )
        updater.apply(completion)
        updater.save()

        # Reload from disk
        fresh = StatusUpdater(status_dir)
        data = fresh.load()
        repo = data["repos"]["bpsai-framework"]
        assert repo["latest_sprint"] == "G3"
        assert repo["sprint_status"] == "complete"
        assert repo["tests"] == 1500
        assert repo["shipped"] == ["Feature A"]

    def test_save_preserves_other_repos(
        self, updater: StatusUpdater, status_dir: Path
    ) -> None:
        completion = SprintCompletion(
            repo_key="bpsai-framework",
            sprint_name="G3",
            test_count=1500,
        )
        updater.apply(completion)
        updater.save()

        fresh = StatusUpdater(status_dir)
        data = fresh.load()
        # CLI repo should be untouched
        cli = data["repos"]["paircoder"]
        assert cli["tests"] == 9900
        assert cli["sprint_status"] == "complete"

    def test_save_without_load_is_noop(self, tmp_path: Path) -> None:
        u = StatusUpdater(tmp_path)
        # No load, no apply — save should not create a file
        u.save()
        assert not (tmp_path / "status.yaml").exists()


# ---------------------------------------------------------------------------
# Hook integration — complete_sprint convenience method
# ---------------------------------------------------------------------------


class TestCompleteSprint:
    def test_complete_sprint_loads_applies_saves(self, status_dir: Path) -> None:
        u = StatusUpdater(status_dir)
        completion = SprintCompletion(
            repo_key="bpsai-framework",
            sprint_name="G3",
            test_count=1500,
            shipped_items=["Engine dispatch"],
        )
        result = u.complete_sprint(completion)
        assert result.success is True

        # Verify persisted
        raw = yaml.safe_load((status_dir / "status.yaml").read_text())
        repo = raw["repos"]["bpsai-framework"]
        assert repo["latest_sprint"] == "G3"
        assert repo["sprint_status"] == "complete"
        assert repo["tests"] == 1500

    def test_complete_sprint_failure_does_not_write(self, status_dir: Path) -> None:
        u = StatusUpdater(status_dir)
        completion = SprintCompletion(
            repo_key="nonexistent",
            sprint_name="S1",
            test_count=100,
        )
        result = u.complete_sprint(completion)
        assert result.success is False

        # Original file should be unchanged
        raw = yaml.safe_load((status_dir / "status.yaml").read_text())
        assert raw == MINIMAL_STATUS


# ---------------------------------------------------------------------------
# Test count refresh from target repo
# ---------------------------------------------------------------------------


class TestRefreshTestCount:
    def test_counts_tests_from_directory(self, tmp_path: Path) -> None:
        """Simulate a repo with test files."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        # Write test files with test functions
        (tests_dir / "test_a.py").write_text(
            "def test_one(): pass\ndef test_two(): pass\n"
        )
        (tests_dir / "test_b.py").write_text(
            "def test_three(): pass\n"
        )

        count = StatusUpdater.count_tests(tmp_path)
        assert count == 3

    def test_no_tests_dir_returns_zero(self, tmp_path: Path) -> None:
        count = StatusUpdater.count_tests(tmp_path)
        assert count == 0

    def test_nested_test_files(self, tmp_path: Path) -> None:
        tests_dir = tmp_path / "tests" / "sub"
        tests_dir.mkdir(parents=True)
        (tests_dir / "test_nested.py").write_text(
            "def test_a(): pass\ndef test_b(): pass\n"
        )
        count = StatusUpdater.count_tests(tmp_path)
        assert count == 2
