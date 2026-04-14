"""Dispatcher — launches Claude Code sessions with enforcement."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional

from computer.orchestration.classifier import detect_repo_type, select_enforcement
from computer.orchestration.config import (
    CREDENTIAL_KEYS,
    CREDENTIAL_PATTERNS,
    DEFAULT_ALLOWED_TOOLS,
    DispatchConfig,
    DispatchError,
    DispatchMode,
    DispatchResult,
    DispatchStatus,
    EnforcementMode,
)


def scrub_environment(env: dict[str, str]) -> dict[str, str]:
    """Return a copy of env with credential keys removed."""
    return {
        k: v for k, v in env.items()
        if k not in CREDENTIAL_KEYS and not CREDENTIAL_PATTERNS.search(k)
    }


def build_command(
    repo_path: Path, prompt: str, enforcement: EnforcementMode,
) -> list[str]:
    """Build the claude CLI command with enforcement flags."""
    cmd = ["claude", "-p"]
    if enforcement == EnforcementMode.ALLOWED_TOOLS:
        cmd.extend(["--allowedTools", ",".join(DEFAULT_ALLOWED_TOOLS)])
    cmd.append(prompt)
    return cmd


class Dispatcher:
    """Launches Claude Code sessions in target repos with enforcement."""

    def dispatch(
        self, repo_path: Path, prompt: str,
        enforcement: Optional[EnforcementMode] = None,
    ) -> DispatchResult:
        """Dispatch a Claude Code session to the target repo."""
        repo_path = Path(repo_path)
        if enforcement is None:
            repo_type = detect_repo_type(repo_path)
            enforcement = select_enforcement(repo_type)
        if not isinstance(enforcement, EnforcementMode):
            raise DispatchError("Dispatch requires enforcement.")

        env = scrub_environment(dict(os.environ))
        cmd = build_command(repo_path, prompt, enforcement)

        completed = subprocess.run(
            cmd, cwd=repo_path, env=env,
            capture_output=True, text=True,
        )
        output = completed.stdout if completed.returncode == 0 else completed.stderr
        status = (
            DispatchStatus.COMPLETE if completed.returncode == 0
            else DispatchStatus.FAILED
        )
        return DispatchResult(
            success=completed.returncode == 0,
            output=output,
            enforcement=enforcement,
            method="subprocess",
            status=status,
        )

    def dispatch_navigator(self, config: DispatchConfig) -> DispatchResult:
        """Dispatch a navigator session using a DispatchConfig."""
        repo_path = Path(config.repo_path)
        enforcement = config.enforcement
        if enforcement is None:
            repo_type = detect_repo_type(repo_path)
            enforcement = select_enforcement(repo_type)
        if not isinstance(enforcement, EnforcementMode):
            raise DispatchError("Dispatch requires enforcement.")

        env = scrub_environment(dict(os.environ))
        cmd = build_command(repo_path, config.prompt, enforcement)

        completed = subprocess.run(
            cmd, cwd=repo_path, env=env,
            capture_output=True, text=True,
        )
        output = completed.stdout if completed.returncode == 0 else completed.stderr
        status = (
            DispatchStatus.COMPLETE if completed.returncode == 0
            else DispatchStatus.FAILED
        )
        result = DispatchResult(
            success=completed.returncode == 0,
            output=output,
            enforcement=enforcement,
            method="subprocess",
            status=status,
        )
        if config.on_complete:
            config.on_complete(result)
        return result
