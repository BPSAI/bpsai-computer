"""Parse backlog markdown into structured task data.

Accepts any alphanumeric task ID prefix (T35.1, B5.1, G3.P1, BP0, etc.).
The regex pattern ``[A-Za-z][\\w.]*\\d[\\w.]*`` matches any ID that starts
with a letter and contains at least one digit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedTask:
    """A task extracted from a backlog document."""

    id: str
    title: str
    complexity: int
    priority: str
    description: str = ""
    ac_items: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    phase: int = 1


@dataclass
class ParsedBacklog:
    """A fully parsed backlog document."""

    tasks: list[ParsedTask] = field(default_factory=list)


# ### T35.1 — Title | Cx: 80 | P0  (any prefix: T, B, G, BP, etc.)
_TASK_HEADER = re.compile(
    r"^###\s+([A-Za-z][\w.]*\d[\w.]*)\s*\u2014\s*(.+?)"
    r"\s*\|\s*Cx:\s*(\d+)\s*\|\s*(P\d)\s*$"
)
_PHASE_HEADER = re.compile(r"^###\s+Phase\s+(\d+):")
_AC_ITEM = re.compile(r"^\s*-\s*\[[ x]\]\s*(.+)$")
_DEPENDS_ON = re.compile(r"\*\*Depends on:\*\*\s*(.+)", re.IGNORECASE)


class BacklogParser:
    """Parses backlog markdown into structured data."""

    @staticmethod
    def parse(path: Path) -> ParsedBacklog:
        """Parse a backlog markdown file into a ParsedBacklog."""
        content = Path(path).read_text(encoding="utf-8")
        lines = content.split("\n")
        tasks: list[ParsedTask] = []
        current_phase = 1
        i = 0

        while i < len(lines):
            line = lines[i]

            phase_match = _PHASE_HEADER.match(line)
            if phase_match:
                current_phase = int(phase_match.group(1))
                i += 1
                continue

            task_match = _TASK_HEADER.match(line)
            if task_match:
                task, i = _parse_task_block(
                    lines, i, task_match, current_phase,
                )
                tasks.append(task)
                continue

            i += 1

        return ParsedBacklog(tasks=tasks)


def _parse_task_block(
    lines: list[str],
    start: int,
    header_match: re.Match,
    phase: int,
) -> tuple[ParsedTask, int]:
    """Parse a single task block starting from its header line."""
    task_id = header_match.group(1)
    title = header_match.group(2).strip().rstrip(" |")
    complexity = int(header_match.group(3))
    priority = header_match.group(4)

    body_lines = _collect_block_lines(lines, start + 1)
    description = _extract_description(body_lines)
    ac_items = _extract_ac_items(body_lines)
    depends_on = _extract_depends_on(body_lines)

    return ParsedTask(
        id=task_id,
        title=title,
        complexity=complexity,
        priority=priority,
        description=description,
        ac_items=ac_items,
        depends_on=depends_on,
        phase=phase,
    ), start + 1 + len(body_lines)


def _collect_block_lines(lines: list[str], start: int) -> list[str]:
    """Collect lines belonging to a task block until the next header."""
    block: list[str] = []
    for i in range(start, len(lines)):
        if _TASK_HEADER.match(lines[i]) or _PHASE_HEADER.match(lines[i]):
            break
        block.append(lines[i])
    return block


def _extract_description(lines: list[str]) -> str:
    """Extract description text from task block lines."""
    desc_lines: list[str] = []
    capturing = False
    for line in lines:
        if line.strip().startswith("**Description:**"):
            desc_lines.append(
                line.split("**Description:**", 1)[1].strip(),
            )
            capturing = True
            continue
        if capturing:
            if line.strip().startswith("**"):
                break
            if line.strip():
                desc_lines.append(line.strip())
    return " ".join(desc_lines).strip()


def _extract_ac_items(lines: list[str]) -> list[str]:
    """Extract acceptance criteria checkboxes from task block."""
    items: list[str] = []
    in_ac = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("**AC:**") or stripped.startswith(
            "**Acceptance criteria:**"
        ):
            in_ac = True
            continue
        if in_ac:
            match = _AC_ITEM.match(line)
            if match:
                items.append(match.group(1).strip())
            elif stripped.startswith("**") or _TASK_HEADER.match(line):
                in_ac = False
    return items


def _extract_depends_on(lines: list[str]) -> list[str]:
    """Extract dependency references from task block."""
    for line in lines:
        match = _DEPENDS_ON.search(line)
        if match:
            text = match.group(1).strip()
            if text.lower() not in ("none", "n/a", ""):
                return re.findall(r"[A-Za-z][\w.]*\d[\w.]*", text)
    return []
