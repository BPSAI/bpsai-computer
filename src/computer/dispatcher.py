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
    """Parse a raw A2A message into a DispatchMessage.

    Supports two formats:
    - Structured: content is JSON with agent, target, prompt keys
    - Plain: content is the prompt text, to_project is the target agent
    """
    try:
        content = json.loads(raw["content"])
        return DispatchMessage(
            message_id=raw["id"],
            agent=content.get("agent", raw.get("to_project", "driver")),
            target=content["target"],
            prompt=content["prompt"],
        )
    except (json.JSONDecodeError, KeyError):
        # Plain text format — content is the prompt, to_project is the target
        to_project = raw.get("to_project", "")
        return DispatchMessage(
            message_id=raw["id"],
            agent=to_project.replace("bpsai-", "") if to_project.startswith("bpsai-") else "driver",
            target=to_project if "/" not in to_project else to_project,
            prompt=raw.get("content", ""),
        )


class DispatchExecutor:
    """Executes dispatches by launching Claude Code as a subprocess."""

    def __init__(self, config: DaemonConfig) -> None:
        self.config = config
        self.workspace_root = Path(config.workspace_root)

    async def execute(
        self,
        msg: DispatchMessage,
        streamer: object | None = None,
    ) -> DispatchResult:
        """Launch Claude Code in the target repo directory.

        If *streamer* is provided, stdout/stderr lines are fed to it
        incrementally. Final result is always returned.
        """
        repo_dir = self.workspace_root / msg.target
        if not repo_dir.is_dir():
            return DispatchResult(
                message_id=msg.message_id,
                success=False,
                output=f"Repository not found: {msg.target} (looked in {repo_dir})",
            )

        log.info("Dispatching: %s in %s", msg.agent, repo_dir)
        try:
            return await self._run_process(msg, repo_dir, streamer)
        except Exception as exc:
            return DispatchResult(
                message_id=msg.message_id, success=False,
                output=f"Execution error: {exc}",
            )

    async def _run_process(
        self, msg: DispatchMessage, repo_dir: Path, streamer: object | None,
    ) -> DispatchResult:
        """Spawn subprocess, read streams line-by-line, build result."""
        cmd = ["claude", "-p", msg.prompt, "--dangerously-skip-permissions"]
        proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=str(repo_dir),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_lines, stderr_lines = await asyncio.wait_for(
                self._read_streams(proc, streamer),
                timeout=self.config.process_timeout,
            )
        except (asyncio.TimeoutError, TimeoutError):
            await self._kill_process(proc)
            log.warning("Dispatch timed out: %s", msg.message_id)
            return DispatchResult(
                msg.message_id, success=False,
                output=f"Process timeout after {self.config.process_timeout}s",
            )
        await proc.wait()
        return self._build_result(msg, proc.returncode, stdout_lines, stderr_lines)

    @staticmethod
    def _build_result(
        msg: DispatchMessage, returncode: int,
        stdout_lines: list[str], stderr_lines: list[str],
    ) -> DispatchResult:
        stdout_text = scrub_credentials("\n".join(stdout_lines))
        stderr_text = scrub_credentials("\n".join(stderr_lines))
        if returncode == 0:
            return DispatchResult(msg.message_id, success=True, output=stdout_text)
        return DispatchResult(
            msg.message_id, success=False,
            output=f"Exit code {returncode}\n--- stdout ---\n{stdout_text}\n--- stderr ---\n{stderr_text}",
        )

    @staticmethod
    async def _kill_process(proc: asyncio.subprocess.Process) -> None:
        try:
            proc.kill()
            await proc.wait()
        except Exception:
            pass

    @staticmethod
    async def _read_stream(
        stream: asyncio.StreamReader,
        stream_name: str,
        collected: list[str],
        streamer: object | None,
    ) -> None:
        """Read a stream line-by-line, feeding each line to the streamer."""
        while True:
            raw = await stream.readline()
            if not raw:
                break
            line = raw.decode(errors="replace").rstrip("\n").rstrip("\r")
            collected.append(line)
            if streamer is not None:
                streamer.add_line(line, stream=stream_name)

    @staticmethod
    async def _read_streams(
        proc: asyncio.subprocess.Process,
        streamer: object | None,
    ) -> tuple[list[str], list[str]]:
        """Read stdout and stderr concurrently, line-by-line."""
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []
        await asyncio.gather(
            DispatchExecutor._read_stream(
                proc.stdout, "stdout", stdout_lines, streamer
            ),
            DispatchExecutor._read_stream(
                proc.stderr, "stderr", stderr_lines, streamer
            ),
        )
        return stdout_lines, stderr_lines
