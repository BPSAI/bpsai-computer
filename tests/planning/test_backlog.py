"""Tests for backlog markdown parser.

Covers: T prefix, B prefix, G prefix, BP prefix, mixed prefixes,
acceptance criteria extraction, dependency parsing, and round-trip
validation with BacklogRenderer output.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from computer.planning.backlog import BacklogParser, ParsedBacklog


class TestTaskIdPrefixes:
    """Parser must accept any alphanumeric prefix before the numeric ID."""

    def test_t_prefix(self, tmp_path):
        md = _write_backlog(tmp_path, "t.md", task_line="### T35.1 — Task A | Cx: 10 | P0")
        result = BacklogParser.parse(md)
        assert len(result.tasks) == 1
        assert result.tasks[0].id == "T35.1"

    def test_b_prefix(self, tmp_path):
        md = _write_backlog(tmp_path, "b.md", task_line="### B5.1 — Task B | Cx: 15 | P1")
        result = BacklogParser.parse(md)
        assert result.tasks[0].id == "B5.1"

    def test_g_prefix_with_dot(self, tmp_path):
        md = _write_backlog(tmp_path, "g.md", task_line="### G3.P1 — Dispatch | Cx: 40 | P0")
        result = BacklogParser.parse(md)
        assert result.tasks[0].id == "G3.P1"

    def test_bp_prefix(self, tmp_path):
        md = _write_backlog(tmp_path, "bp.md", task_line="### BP0 — Parser Fix | Cx: 20 | P0")
        result = BacklogParser.parse(md)
        assert result.tasks[0].id == "BP0"

    def test_mixed_prefixes_in_one_backlog(self, tmp_path):
        content = dedent("""\
            # Mixed Backlog

            ### T1.1 — First | Cx: 10 | P0

            **Description:** First task

            ### BP2 — Second | Cx: 15 | P1

            **Description:** Second task

            ### G3.P1 — Third | Cx: 20 | P0

            **Description:** Third task
        """)
        p = tmp_path / "mixed.md"
        p.write_text(content)
        result = BacklogParser.parse(p)
        assert len(result.tasks) == 3
        assert [t.id for t in result.tasks] == ["T1.1", "BP2", "G3.P1"]


class TestAcceptanceCriteria:
    def test_extracts_ac_items(self, tmp_path):
        content = dedent("""\
            # Backlog

            ### T1.1 — Task | Cx: 10 | P0

            **Description:** A task

            **AC:**
            - [ ] First criterion
            - [ ] Second criterion
        """)
        p = tmp_path / "ac.md"
        p.write_text(content)
        result = BacklogParser.parse(p)
        assert result.tasks[0].ac_items == ["First criterion", "Second criterion"]

    def test_checked_ac_items_extracted(self, tmp_path):
        content = dedent("""\
            # Backlog

            ### T1.1 — Task | Cx: 10 | P0

            **Description:** A task

            **AC:**
            - [x] Done item
            - [ ] Pending item
        """)
        p = tmp_path / "ac2.md"
        p.write_text(content)
        result = BacklogParser.parse(p)
        assert len(result.tasks[0].ac_items) == 2


class TestDependencies:
    def test_extracts_depends_on(self, tmp_path):
        content = dedent("""\
            # Backlog

            ### T1.2 — Task | Cx: 10 | P0

            **Description:** Depends on previous

            **Depends on:** T1.1
        """)
        p = tmp_path / "deps.md"
        p.write_text(content)
        result = BacklogParser.parse(p)
        assert result.tasks[0].depends_on == ["T1.1"]

    def test_multiple_dependencies(self, tmp_path):
        content = dedent("""\
            # Backlog

            ### BP3 — Orchestrator | Cx: 30 | P0

            **Description:** Needs both

            **Depends on:** BP1, BP2
        """)
        p = tmp_path / "multi_deps.md"
        p.write_text(content)
        result = BacklogParser.parse(p)
        assert set(result.tasks[0].depends_on) == {"BP1", "BP2"}


class TestPhases:
    def test_phase_header_sets_phase(self, tmp_path):
        content = dedent("""\
            # Backlog

            ### Phase 1: Foundation

            ### T1.1 — First | Cx: 10 | P0

            **Description:** Phase 1 task

            ### Phase 2: Integration

            ### T1.2 — Second | Cx: 15 | P1

            **Description:** Phase 2 task
        """)
        p = tmp_path / "phases.md"
        p.write_text(content)
        result = BacklogParser.parse(p)
        assert result.tasks[0].phase == 1
        assert result.tasks[1].phase == 2


class TestExistingBacklogs:
    """Verify real backlogs in the repo parse without error."""

    @pytest.fixture
    def backlogs_dir(self):
        return Path(__file__).parent.parent / "plans" / "backlogs"

    def test_bot_sprint_35_parses(self, backlogs_dir):
        p = backlogs_dir / "bot-sprint-35.md"
        if not p.exists():
            pytest.skip("bot-sprint-35.md not present")
        result = BacklogParser.parse(p)
        assert len(result.tasks) > 0
        assert all(t.id.startswith("T35.") for t in result.tasks)

    def test_framework_computer_dispatch_parses(self, backlogs_dir):
        p = backlogs_dir / "framework-computer-dispatch.md"
        if not p.exists():
            pytest.skip("framework-computer-dispatch.md not present")
        result = BacklogParser.parse(p)
        assert len(result.tasks) > 0


class TestRoundTrip:
    """Rendered backlogs must parse back correctly."""

    def test_rendered_backlog_round_trips(self, tmp_path):
        from computer.planning.render import BacklogRenderer
        from computer.planning.types import SprintBacklog, SprintTask

        backlog = SprintBacklog(
            sprint_id="Bot-S35",
            repo="paircoder_bot",
            theme="Test",
            goal="Test goal",
            tasks=[
                SprintTask("T35.1", "First Task", "Do something", 10, "P0"),
                SprintTask("T35.2", "Second Task", "Do more", 15, "P1"),
            ],
        )
        renderer = BacklogRenderer()
        md = renderer.render(backlog)

        p = tmp_path / "rendered.md"
        p.write_text(md)
        result = BacklogParser.parse(p)

        assert len(result.tasks) == 2
        assert result.tasks[0].id == "T35.1"
        assert result.tasks[1].id == "T35.2"
        assert result.tasks[0].title == "First Task"
        assert result.tasks[0].complexity == 10
        assert result.tasks[0].priority == "P0"


# ---------- helpers ----------


def _write_backlog(tmp_path: Path, name: str, task_line: str) -> Path:
    content = f"# Test Backlog\n\n{task_line}\n\n**Description:** A test task\n"
    p = tmp_path / name
    p.write_text(content)
    return p
