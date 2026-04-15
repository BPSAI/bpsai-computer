"""Delivers rendered sprint backlogs to target repo directories.

Key invariant: delivery produces a file but NEVER triggers dispatch.
The human review gate is enforced by setting dispatched=False on every
delivery result. Only BP3 (Navigator Dispatch Orchestration) will
wire delivery → approval → dispatch.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from computer.planning.backlog import BacklogParser
from computer.planning.render import BacklogRenderer
from computer.planning.types import SprintBacklog


@dataclass
class DeliveryResult:
    """Outcome of a backlog delivery attempt."""

    success: bool
    path: Path
    error: str = ""
    dispatched: bool = False
    is_draft: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "path": str(self.path),
            "error": self.error,
            "dispatched": self.dispatched,
            "is_draft": self.is_draft,
        }


class BacklogDeliverer:
    """Writes rendered backlogs to target directories.

    Never auto-dispatches. The dispatched field is always False.
    """

    def __init__(self, renderer: BacklogRenderer | None = None) -> None:
        self._renderer = renderer or BacklogRenderer()

    @staticmethod
    def _validate_round_trip(
        md: str, backlog: SprintBacklog,
    ) -> str:
        """Validate rendered markdown parses back to matching tasks.

        Returns an error message if validation fails, empty string on success.
        """
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8",
        ) as f:
            f.write(md)
            f.flush()
            tmp = Path(f.name)

        try:
            parsed = BacklogParser.parse(tmp)
        finally:
            tmp.unlink(missing_ok=True)

        if len(parsed.tasks) != len(backlog.tasks):
            return (
                f"Validation failed: rendered {len(backlog.tasks)} tasks "
                f"but parser found {len(parsed.tasks)}"
            )

        for expected, actual in zip(backlog.tasks, parsed.tasks):
            if expected.task_id and expected.task_id != actual.id:
                return (
                    f"Validation failed: expected task ID "
                    f"'{expected.task_id}' but parsed '{actual.id}'"
                )

        return ""

    def deliver(
        self,
        backlog: SprintBacklog,
        target_dir: Path,
        filename: str,
        draft: bool = False,
        overwrite: bool = False,
    ) -> DeliveryResult:
        """Render and write a backlog to target_dir/filename."""
        target_dir = Path(target_dir)

        if not target_dir.exists():
            return DeliveryResult(
                success=False,
                path=target_dir / filename,
                error=f"Target directory does not exist: {target_dir}",
            )

        if draft:
            stem = Path(filename).stem
            suffix = Path(filename).suffix
            filename = f"{stem}.draft{suffix}"

        dest = target_dir / filename

        if dest.exists() and not overwrite:
            return DeliveryResult(
                success=False,
                path=dest,
                error=f"File already exists: {dest}",
            )

        md = self._renderer.render(backlog)

        error = self._validate_round_trip(md, backlog)
        if error:
            return DeliveryResult(
                success=False, path=dest, error=error,
            )

        dest.write_text(md, encoding="utf-8")

        return DeliveryResult(
            success=True,
            path=dest,
            dispatched=False,
            is_draft=draft,
        )
