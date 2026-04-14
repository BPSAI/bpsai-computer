"""Tests for backlog delivery to target repos.

Covers: file writing, path validation, human review gate,
and draft-only semantics.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from computer.planning.deliver import BacklogDeliverer, DeliveryResult
from computer.planning.render import BacklogRenderer
from computer.planning.types import SprintBacklog, SprintTask


def _sample_backlog() -> SprintBacklog:
    return SprintBacklog(
        sprint_id="Bot-S35",
        repo="paircoder_bot",
        theme="Test",
        goal="Test goal",
        tasks=[
            SprintTask("T35.1", "Task A", "Desc", 10, "P0"),
        ],
    )


class TestBacklogDeliverer:
    def test_delivers_to_target_path(self, tmp_path):
        target = tmp_path / "plans" / "backlogs"
        target.mkdir(parents=True)

        deliverer = BacklogDeliverer()
        result = deliverer.deliver(
            backlog=_sample_backlog(),
            target_dir=target,
            filename="bot-sprint-35.md",
        )
        assert isinstance(result, DeliveryResult)
        assert result.success is True
        assert result.path.exists()
        content = result.path.read_text()
        assert "Bot-S35" in content

    def test_delivery_creates_draft_file(self, tmp_path):
        """Delivered files are drafts — filename indicates draft status."""
        target = tmp_path / "plans" / "backlogs"
        target.mkdir(parents=True)

        deliverer = BacklogDeliverer()
        result = deliverer.deliver(
            backlog=_sample_backlog(),
            target_dir=target,
            filename="bot-sprint-35.md",
            draft=True,
        )
        assert result.success is True
        assert "draft" in result.path.name.lower() or result.is_draft

    def test_delivery_rejects_nonexistent_dir(self, tmp_path):
        deliverer = BacklogDeliverer()
        result = deliverer.deliver(
            backlog=_sample_backlog(),
            target_dir=tmp_path / "nonexistent",
            filename="test.md",
        )
        assert result.success is False
        assert "not exist" in result.error.lower() or "not found" in result.error.lower()

    def test_delivery_does_not_overwrite_without_flag(self, tmp_path):
        target = tmp_path / "plans" / "backlogs"
        target.mkdir(parents=True)
        existing = target / "bot-sprint-35.md"
        existing.write_text("# Existing content\n")

        deliverer = BacklogDeliverer()
        result = deliverer.deliver(
            backlog=_sample_backlog(),
            target_dir=target,
            filename="bot-sprint-35.md",
        )
        assert result.success is False
        assert "exists" in result.error.lower()

    def test_delivery_overwrites_with_flag(self, tmp_path):
        target = tmp_path / "plans" / "backlogs"
        target.mkdir(parents=True)
        existing = target / "bot-sprint-35.md"
        existing.write_text("# Old content\n")

        deliverer = BacklogDeliverer()
        result = deliverer.deliver(
            backlog=_sample_backlog(),
            target_dir=target,
            filename="bot-sprint-35.md",
            overwrite=True,
        )
        assert result.success is True
        assert "Bot-S35" in result.path.read_text()

    def test_human_review_gate_not_auto_dispatched(self, tmp_path):
        """Delivery produces a file but does NOT trigger dispatch."""
        target = tmp_path / "plans" / "backlogs"
        target.mkdir(parents=True)

        deliverer = BacklogDeliverer()
        result = deliverer.deliver(
            backlog=_sample_backlog(),
            target_dir=target,
            filename="bot-sprint-35.md",
        )
        assert result.success is True
        assert result.dispatched is False

    def test_validates_parse_before_writing(self, tmp_path):
        """Deliverer validates rendered markdown parses back correctly."""
        target = tmp_path / "plans" / "backlogs"
        target.mkdir(parents=True)

        deliverer = BacklogDeliverer()
        result = deliverer.deliver(
            backlog=_sample_backlog(),
            target_dir=target,
            filename="bot-sprint-35.md",
        )
        assert result.success is True
        # The file should exist and parse back to the same task count
        from computer.planning.backlog import BacklogParser
        parsed = BacklogParser.parse(result.path)
        assert len(parsed.tasks) == 1
        assert parsed.tasks[0].id == "T35.1"

    def test_validation_catches_empty_tasks(self, tmp_path):
        """Deliverer rejects backlogs that render with no parseable tasks."""
        target = tmp_path / "plans" / "backlogs"
        target.mkdir(parents=True)

        # A backlog with tasks that have empty IDs should fail validation
        bad_backlog = SprintBacklog(
            sprint_id="Bot-S35",
            repo="paircoder_bot",
            theme="Test",
            goal="Test goal",
            tasks=[
                SprintTask("", "No ID Task", "Desc", 10, "P0"),
            ],
        )
        deliverer = BacklogDeliverer()
        result = deliverer.deliver(
            backlog=bad_backlog,
            target_dir=target,
            filename="bad.md",
        )
        assert result.success is False
        assert "validation" in result.error.lower() or "parse" in result.error.lower()

    def test_delivery_result_to_dict(self, tmp_path):
        target = tmp_path / "plans" / "backlogs"
        target.mkdir(parents=True)

        deliverer = BacklogDeliverer()
        result = deliverer.deliver(
            backlog=_sample_backlog(),
            target_dir=target,
            filename="test.md",
        )
        d = result.to_dict()
        assert "success" in d
        assert "path" in d
        assert "dispatched" in d
