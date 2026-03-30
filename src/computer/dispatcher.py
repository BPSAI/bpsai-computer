"""Dispatch execution: parse messages, launch Claude Code subprocess."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path

from computer.config import DaemonConfig
from computer.scrubber import scrub_credentials

log = logging.getLogger(__name__)


@dataclass
class DispatchMessage:
    """Parsed dispatch message."""
    message_id: str
    agent: str
    target: str
    prompt: str


@dataclass
class DispatchResult:
    """Result of a dispatch execution."""
    message_id: str
    success: bool
    output: str


def parse_dispatch(raw: dict) -> DispatchMessage:
    """Parse a raw A2A message into a DispatchMessage."""
    content = json.loads(raw["content"])
    return DispatchMessage(
        message_id=raw["id"],
        agent=content["agent"],
        target=content["target"],
        prompt=content["prompt"],
    )


class DispatchExecutor:
    """Executes dispatches by launching Claude Code as a subprocess."""

    def __init__(self, config: DaemonConfig) -> None:
        self.config = config
        self.workspace_root = Path(config.workspace_root)

    async def execute(self, msg: DispatchMessage) -> DispatchResult:
        """Launch Claude Code in the target repo directory."""
        repo_dir = self.workspace_root / msg.target
        if not repo_dir.is_dir():
            return DispatchResult(
                message_id=msg.message_id,
                success=False,
                output=f"Repository not found: {msg.target} (looked in {repo_dir})",
            )

        cmd = [
            "claude",
            "-p", msg.prompt,
            "--dangerously-skip-permissions",
        ]

        log.info("Dispatching: %s in %s", msg.agent, repo_dir)
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(repo_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.config.process_timeout,
            )

            stdout_text = scrub_credentials(stdout.decode(errors="replace"))
            stderr_text = scrub_credentials(stderr.decode(errors="replace"))

            if proc.returncode == 0:
                return DispatchResult(
                    message_id=msg.message_id,
                    success=True,
                    output=stdout_text,
                )
            else:
                return DispatchResult(
                    message_id=msg.message_id,
                    success=False,
                    output=f"Exit code {proc.returncode}\n--- stdout ---\n{stdout_text}\n--- stderr ---\n{stderr_text}",
                )

        except (asyncio.TimeoutError, TimeoutError):
            log.warning("Dispatch timed out: %s", msg.message_id)
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
            return DispatchResult(
                message_id=msg.message_id,
                success=False,
                output=f"Process timeout after {self.config.process_timeout}s",
            )
        except Exception as exc:
            return DispatchResult(
                message_id=msg.message_id,
                success=False,
                output=f"Execution error: {exc}",
            )
