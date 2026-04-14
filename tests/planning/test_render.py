"""Tests for backlog markdown rendering.

Verifies that SprintBacklog renders to markdown matching existing
backlog style (Bot-S34, Bot-S35, framework-computer-dispatch).
"""

from __future__ import annotations

import pytest

from computer.planning.render import BacklogRenderer
from computer.planning.types import SprintBacklog, SprintTask


def _sample_backlog() -> SprintBacklog:
    return SprintBacklog(
        sprint_id="Bot-S35",
        repo="paircoder_bot",
        theme="Metis Phase 3",
        goal="Close remaining Metis feedback loops and harden standup output.",
        author="Framework Navigator (CNS)",
        date="2026-03-28",
        portfolio_alignment="G3, HYP-008/009, execution-priorities.md",
        predecessor="Bot-S34 (Metis closes the loop, 80cx)",
        tasks=[
            SprintTask(
                task_id="T35.1",
                title="Closed Hypothesis Standup",
                description="Show closed hypotheses with outcome badges in standup report.",
                complexity=10,
                priority="P0",
                acceptance_criteria=[
                    "Closed hypotheses appear in standup",
                    "Outcome badges shown (Validated, Invalidated, Abandoned)",
                ],
                files=["src/metis/standup.py"],
                phase=1,
            ),
            SprintTask(
                task_id="T35.2",
                title="Standup JSON Sidecar",
                description="Generate machine-readable JSON alongside markdown standup.",
                complexity=15,
                priority="P1",
                acceptance_criteria=[
                    "JSON file written alongside markdown",
                    "Schema matches dashboard expectations",
                ],
                files=["src/metis/standup.py", "scripts/generate-standup.mjs"],
                phase=1,
            ),
        ],
    )


class TestBacklogRenderer:
    def test_renders_markdown(self):
        renderer = BacklogRenderer()
        md = renderer.render(_sample_backlog())
        assert isinstance(md, str)
        assert len(md) > 100

    def test_has_title_with_sprint_and_theme(self):
        renderer = BacklogRenderer()
        md = renderer.render(_sample_backlog())
        assert "Bot-S35" in md
        assert "Metis Phase 3" in md

    def test_has_metadata_header(self):
        renderer = BacklogRenderer()
        md = renderer.render(_sample_backlog())
        assert "Authored by:" in md
        assert "Framework Navigator (CNS)" in md
        assert "paircoder_bot" in md

    def test_has_sprint_goal(self):
        renderer = BacklogRenderer()
        md = renderer.render(_sample_backlog())
        assert "Sprint Goal" in md
        assert "feedback loops" in md

    def test_has_task_sections(self):
        renderer = BacklogRenderer()
        md = renderer.render(_sample_backlog())
        assert "T35.1" in md
        assert "Closed Hypothesis Standup" in md
        assert "T35.2" in md
        assert "Cx: 10" in md

    def test_has_acceptance_criteria_checkboxes(self):
        renderer = BacklogRenderer()
        md = renderer.render(_sample_backlog())
        assert "- [ ]" in md
        assert "Closed hypotheses appear in standup" in md

    def test_has_files_section(self):
        renderer = BacklogRenderer()
        md = renderer.render(_sample_backlog())
        assert "src/metis/standup.py" in md

    def test_has_summary_table(self):
        renderer = BacklogRenderer()
        md = renderer.render(_sample_backlog())
        assert "Summary" in md
        assert "| T35.1" in md
        assert "| T35.2" in md
        assert "Total" in md
        # Total complexity = 10 + 15 = 25
        assert "25" in md

    def test_empty_backlog_renders(self):
        backlog = SprintBacklog(
            sprint_id="S1", repo="test", theme="Empty", goal="Nothing", tasks=[]
        )
        renderer = BacklogRenderer()
        md = renderer.render(backlog)
        assert "S1" in md
        assert "Total" in md
