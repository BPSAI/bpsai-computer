"""Parsers for Metis standup and execution-priorities.md.

Extracted from sprint_planner.py to keep files under 200 lines.
"""

from __future__ import annotations

import re
from pathlib import Path

from computer.planning.types import (
    FINDING_RE,
    HYP_ID_RE,
    STALE_RE,
    PriorityItem,
    StandupItem,
)

_TIER_HEADER_RE = re.compile(r"^#{2,3}\s+.*[Tt]ier\s+(\d+)")
_TABLE_ROW_RE = re.compile(
    r"^\|\s*(?P<item>[^|]+)\|\s*(?P<repo>[^|]+)\|\s*(?P<effort>[^|]+)\|"
    r"\s*(?P<extra1>[^|]+)\|\s*(?P<extra2>[^|]*)\|",
)


def parse_standup(path: Path) -> list[StandupItem]:
    """Parse a Metis standup markdown file into actionable items."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Standup file not found: {path}")

    text = path.read_text()
    items: list[StandupItem] = []

    for line in text.splitlines():
        line = line.strip()
        m = FINDING_RE.match(line)
        if m:
            hyp_match = HYP_ID_RE.search(m.group("desc"))
            items.append(StandupItem(
                source="metis",
                description=m.group("desc").strip(),
                severity=m.group("severity").lower(),
                hypothesis_id=hyp_match.group(0) if hyp_match else None,
            ))
            continue
        m = STALE_RE.match(line)
        if m:
            items.append(StandupItem(
                source="metis",
                description=m.group("desc").strip(),
                severity="high",
                hypothesis_id=m.group("hyp_id"),
            ))

    return items


def read_execution_priorities(path: Path) -> list[PriorityItem]:
    """Parse execution-priorities.md and return tier-ordered items."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Priorities file not found: {path}")

    text = path.read_text()
    items: list[PriorityItem] = []
    current_tier = 0

    for line in text.splitlines():
        m = _TIER_HEADER_RE.match(line.strip())
        if m:
            current_tier = int(m.group(1))
            continue
        if current_tier == 0:
            continue
        m = _TABLE_ROW_RE.match(line.strip())
        if m:
            item_name = m.group("item").strip()
            if item_name.startswith("---") or item_name == "Item":
                continue
            items.append(PriorityItem(
                item=item_name,
                repo=m.group("repo").strip(),
                effort=m.group("effort").strip(),
                tier=current_tier,
                notes=m.group("extra2").strip(),
            ))

    items.sort(key=lambda i: i.tier)
    return items
