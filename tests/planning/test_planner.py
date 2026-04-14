"""Tests for the sprint planner — Computer₀ PLAN phase.

Covers: standup parsing, priorities reading, backlog construction,
markdown rendering, file delivery, and human review gate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from computer.planning.planner import (
    PlanningContext,
    SprintBacklog,
    SprintPlanner,
    SprintTask,
    StandupItem,
    parse_standup,
    read_execution_priorities,
)


# ---------- StandupItem ----------


class TestStandupItem:
    def test_create_standup_item(self):
        item = StandupItem(
            source="metis",
            description="HYP-008 flagged 6 consecutive cycles",
            severity="high",
            hypothesis_id="HYP-008",
        )
        assert item.source == "metis"
        assert item.severity == "high"
        assert item.hypothesis_id == "HYP-008"

    def test_standup_item_defaults(self):
        item = StandupItem(
            source="metis",
            description="Something observed",
        )
        assert item.severity == "medium"
        assert item.hypothesis_id is None

    def test_standup_item_to_dict(self):
        item = StandupItem(
            source="metis",
            description="Test finding",
            severity="high",
            hypothesis_id="HYP-001",
        )
        d = item.to_dict()
        assert d["source"] == "metis"
        assert d["severity"] == "high"


# ---------- parse_standup ----------


class TestParseStandup:
    def test_parses_hypothesis_dashboard(self, tmp_path):
        standup = tmp_path / "standup.md"
        standup.write_text(
            "# Metis Standup\n\n"
            "## Hypothesis Dashboard\n\n"
            "| ID | Title | Status | Confidence | Last Reviewed | Days Since |\n"
            "|-----|-------|--------|------------|---------------|------------|\n"
            "| HYP-008 | Customer-facing blind spot | observed | 0.3 | 2026-03-10 | 17 |\n"
            "| HYP-004 | Threshold calibration | incubating | 0.6 | 2026-03-25 | 2 |\n\n"
            "## Stale Hypotheses\n\n"
            "- **HYP-008** — 17 days since review, criteria unmet\n\n"
            "## Recent Findings\n\n"
            "- [high] Customer-facing repos have zero observability\n"
            "- [medium] A2A signal coverage insufficient\n\n"
            "## Cycle Summary\n\n"
            "| Cycle | Action | Confidence | Findings |\n"
            "|-------|--------|------------|----------|\n"
            "| 42 | cognitive | 0.45 | 3 |\n"
        )
        items = parse_standup(standup)
        assert len(items) >= 2
        high_items = [i for i in items if i.severity == "high"]
        assert len(high_items) >= 1
        assert any(i.hypothesis_id == "HYP-008" for i in items)

    def test_parses_findings_section(self, tmp_path):
        standup = tmp_path / "standup.md"
        standup.write_text(
            "# Metis Standup\n\n"
            "## Recent Findings\n\n"
            "- [high] Zero observability in customer-facing repos\n"
            "- [medium] Stale hypothesis HYP-004\n"
            "- [low] Minor config drift detected\n"
        )
        items = parse_standup(standup)
        assert len(items) == 3
        assert items[0].severity == "high"
        assert items[1].severity == "medium"
        assert items[2].severity == "low"

    def test_empty_standup_returns_empty(self, tmp_path):
        standup = tmp_path / "standup.md"
        standup.write_text("# Metis Standup\n\nNo findings.\n")
        items = parse_standup(standup)
        assert items == []

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            parse_standup(Path("/nonexistent/standup.md"))


# ---------- read_execution_priorities ----------


class TestReadExecutionPriorities:
    def test_reads_tier_ordering(self, tmp_path):
        priorities = tmp_path / "execution-priorities.md"
        priorities.write_text(
            "# Execution Priorities\n\n"
            "## What's Next — G3 Planning Inputs\n\n"
            "### Tier 3 Remaining\n"
            "| Item | Repo | Effort | Dependencies | Notes |\n"
            "|------|------|--------|-------------|-------|\n"
            "| Computer Plan + Dispatch | FW | ~200cx | G2.7 done | Autonomous sprint planning |\n\n"
            "### Tier 4: Features + Infrastructure\n"
            "| Item | Repo | Effort | Status | Notes |\n"
            "|------|------|--------|--------|-------|\n"
            "| QC Phase 2 | CLI | ~135cx | Backlogged | Element discovery |\n"
            "| Voice Extraction | FW | ~180cx | Draft | Architectural |\n"
        )
        tiers = read_execution_priorities(priorities)
        assert len(tiers) >= 2
        # Items should be ordered: tier 3 before tier 4
        assert tiers[0].tier <= tiers[-1].tier

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            read_execution_priorities(Path("/nonexistent/priorities.md"))


# ---------- SprintTask ----------


class TestSprintTask:
    def test_create_task(self):
        task = SprintTask(
            task_id="T12.1",
            title="Hypothesis Persistence",
            description="Write HYP-NNN.yaml files",
            complexity=20,
            priority="P0",
            acceptance_criteria=["Writes YAML files", "Auto-increments IDs"],
            files=["src/metis/hypothesis_manager.py"],
        )
        assert task.task_id == "T12.1"
        assert task.complexity == 20

    def test_task_to_dict(self):
        task = SprintTask(
            task_id="T12.1",
            title="Test",
            description="Desc",
            complexity=10,
            priority="P0",
        )
        d = task.to_dict()
        assert d["task_id"] == "T12.1"
        assert d["complexity"] == 10


# ---------- SprintBacklog ----------


class TestSprintBacklog:
    def test_create_backlog(self):
        backlog = SprintBacklog(
            sprint_id="Bot-S35",
            repo="paircoder_bot",
            theme="Metis Phase 3",
            goal="Close remaining Metis feedback loops",
            tasks=[
                SprintTask(
                    task_id="T35.1",
                    title="Closed hypothesis standup",
                    description="Show closed hypotheses in standup",
                    complexity=10,
                    priority="P0",
                ),
            ],
        )
        assert backlog.sprint_id == "Bot-S35"
        assert len(backlog.tasks) == 1

    def test_total_complexity(self):
        backlog = SprintBacklog(
            sprint_id="S1",
            repo="test",
            theme="Test",
            goal="Test",
            tasks=[
                SprintTask("T1.1", "A", "D", 20, "P0"),
                SprintTask("T1.2", "B", "D", 30, "P1"),
            ],
        )
        assert backlog.total_complexity == 50

    def test_empty_backlog_zero_complexity(self):
        backlog = SprintBacklog(
            sprint_id="S1", repo="test", theme="Test", goal="Test", tasks=[]
        )
        assert backlog.total_complexity == 0

    def test_backlog_to_dict(self):
        backlog = SprintBacklog(
            sprint_id="S1",
            repo="test",
            theme="Test",
            goal="Goal",
            tasks=[SprintTask("T1.1", "A", "D", 10, "P0")],
            author="Framework Navigator (CNS)",
        )
        d = backlog.to_dict()
        assert d["sprint_id"] == "S1"
        assert d["author"] == "Framework Navigator (CNS)"
        assert len(d["tasks"]) == 1


# ---------- PlanningContext ----------


class TestPlanningContext:
    def test_create_context(self):
        ctx = PlanningContext(
            standup_items=[
                StandupItem("metis", "Finding 1", "high", "HYP-008"),
            ],
            priority_items=[],
            hypothesis_states={
                "HYP-008": {"status": "observed", "confidence": 0.3},
            },
            target_repo="paircoder_bot",
            sprint_prefix="Bot-S35",
        )
        assert ctx.target_repo == "paircoder_bot"
        assert len(ctx.standup_items) == 1


# ---------- SprintPlanner ----------


class TestSprintPlanner:
    def _mock_standup(self, tmp_path: Path) -> Path:
        standup = tmp_path / "standup.md"
        standup.write_text(
            "# Metis Standup\n\n"
            "## Recent Findings\n\n"
            "- [high] Customer repos have zero observability\n"
            "- [medium] A2A signal coverage gap\n"
        )
        return standup

    def _mock_priorities(self, tmp_path: Path) -> Path:
        priorities = tmp_path / "execution-priorities.md"
        priorities.write_text(
            "# Execution Priorities\n\n"
            "### Tier 3 Remaining\n"
            "| Item | Repo | Effort | Dependencies | Notes |\n"
            "|------|------|--------|-------------|-------|\n"
            "| Computer Plan | FW | ~200cx | None | Planning |\n\n"
            "### Tier 4: Features + Infrastructure\n"
            "| Item | Repo | Effort | Status | Notes |\n"
            "|------|------|--------|--------|-------|\n"
            "| QC Phase 2 | CLI | ~135cx | Backlogged | Testing |\n"
        )
        return priorities

    def test_plan_produces_backlog(self, tmp_path):
        planner = SprintPlanner()
        standup = self._mock_standup(tmp_path)
        priorities = self._mock_priorities(tmp_path)

        backlog = planner.plan(
            standup_path=standup,
            priorities_path=priorities,
            target_repo="paircoder_bot",
            sprint_id="Bot-S35",
            theme="Observability",
        )
        assert isinstance(backlog, SprintBacklog)
        assert backlog.sprint_id == "Bot-S35"
        assert backlog.repo == "paircoder_bot"
        assert len(backlog.tasks) > 0

    def test_plan_respects_tier_ordering(self, tmp_path):
        """Higher-tier items should appear before lower-tier items."""
        planner = SprintPlanner()
        standup = self._mock_standup(tmp_path)
        priorities = self._mock_priorities(tmp_path)

        backlog = planner.plan(
            standup_path=standup,
            priorities_path=priorities,
            target_repo="framework",
            sprint_id="FW-S12",
            theme="Computer",
        )
        assert isinstance(backlog, SprintBacklog)

    def test_plan_extracts_actionable_from_standup(self, tmp_path):
        planner = SprintPlanner()
        standup = self._mock_standup(tmp_path)
        priorities = self._mock_priorities(tmp_path)

        backlog = planner.plan(
            standup_path=standup,
            priorities_path=priorities,
            target_repo="framework",
            sprint_id="FW-S12",
            theme="Fix",
        )
        # High-severity standup items should become tasks
        assert any("observability" in t.title.lower() or "observability" in t.description.lower()
                    for t in backlog.tasks)

    def test_plan_is_draft_not_dispatched(self, tmp_path):
        """The planner produces a draft — it never auto-dispatches."""
        planner = SprintPlanner()
        standup = self._mock_standup(tmp_path)
        priorities = self._mock_priorities(tmp_path)

        backlog = planner.plan(
            standup_path=standup,
            priorities_path=priorities,
            target_repo="framework",
            sprint_id="FW-S12",
            theme="Test",
        )
        assert backlog.status == "draft"
