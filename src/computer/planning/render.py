"""Renders SprintBacklog to markdown matching existing backlog style.

Output format matches Bot-S34, Bot-S35, and framework-computer-dispatch
backlogs: title with sprint+theme, metadata header, sprint goal,
task sections with acceptance criteria, and summary table.
"""

from __future__ import annotations

from computer.planning.types import SprintBacklog


class BacklogRenderer:
    """Renders a SprintBacklog to markdown."""

    def render(self, backlog: SprintBacklog) -> str:
        """Produce markdown matching the project's backlog format."""
        sections = [
            self._render_title(backlog),
            self._render_metadata(backlog),
            self._render_goal(backlog),
            self._render_tasks(backlog),
            self._render_summary(backlog),
        ]
        return "\n".join(sections)

    @staticmethod
    def _render_title(b: SprintBacklog) -> str:
        return f"# {b.repo} — {b.sprint_id} Backlog ({b.theme})\n"

    @staticmethod
    def _render_metadata(b: SprintBacklog) -> str:
        lines = [f"> **Authored by:** {b.author}"]
        if b.date:
            lines.append(f"> **Date:** {b.date}")
        if b.portfolio_alignment:
            lines.append(f"> **Portfolio alignment:** {b.portfolio_alignment}")
        if b.predecessor:
            lines.append(f"> **Predecessor:** {b.predecessor}")
        lines.append(f"> **Repo:** {b.repo}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _render_goal(b: SprintBacklog) -> str:
        return f"---\n\n## Sprint Goal\n\n{b.goal}\n"

    @staticmethod
    def _render_tasks(b: SprintBacklog) -> str:
        if not b.tasks:
            return "---\n\n## Tasks\n\nNo tasks defined.\n"

        lines = ["---\n", "## Tasks\n"]
        for task in b.tasks:
            lines.append(
                f"### {task.task_id} — {task.title} "
                f"| Cx: {task.complexity} | {task.priority}\n"
            )
            lines.append(f"**Description:** {task.description}\n")

            if task.files:
                lines.append(
                    f"**Files:** {', '.join(f'`{f}`' for f in task.files)}\n"
                )

            if task.acceptance_criteria:
                lines.append("**Acceptance criteria:**")
                for ac in task.acceptance_criteria:
                    lines.append(f"- [ ] {ac}")
                lines.append("")

            lines.append("---\n")

        return "\n".join(lines)

    @staticmethod
    def _render_summary(b: SprintBacklog) -> str:
        lines = [
            "## Summary\n",
            "| Task | Title | Cx | Priority | Phase |",
            "|------|-------|----|----------|-------|",
        ]
        for task in b.tasks:
            lines.append(
                f"| {task.task_id} | {task.title} "
                f"| {task.complexity} | {task.priority} | {task.phase} |"
            )
        lines.append(
            f"| **Total** | | **{b.total_complexity}** | | |"
        )
        lines.append("")
        return "\n".join(lines)
