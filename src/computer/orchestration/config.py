"""Types, constants, and configuration for the dispatch engine."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional


# Keys that are always scrubbed from dispatch environment
CREDENTIAL_KEYS = frozenset({
    "AWS_SECRET_ACCESS_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SESSION_TOKEN",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "GITLAB_TOKEN",
    "DATABASE_URL",
    "REDIS_URL",
    "MONGO_URI",
})

# Pattern fragments that indicate a credential key
CREDENTIAL_PATTERNS = re.compile(
    r"(SECRET|TOKEN|PASSWORD|CREDENTIAL|PRIVATE_KEY|API_KEY)", re.IGNORECASE
)

# Default tools allowed for non-PairCoder repos
DEFAULT_ALLOWED_TOOLS = (
    "Read", "Write", "Edit", "Bash", "Glob", "Grep",
)


class RepoType(Enum):
    PAIRCODER = "paircoder"
    STANDARD = "standard"


class EnforcementMode(Enum):
    CONTAINED_AUTO = "contained-auto"
    ALLOWED_TOOLS = "allowed-tools"


class DispatchMode(Enum):
    SUBPROCESS = "subprocess"
    RC = "rc"


class DispatchStatus(Enum):
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class CompletionStatus(Enum):
    """Lifecycle status for a dispatched navigator session."""

    PENDING = "pending"
    RUNNING = "running"
    PR_READY = "pr_ready"
    MERGED = "merged"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        return self in (CompletionStatus.MERGED, CompletionStatus.FAILED)


class DispatchError(Exception):
    """Raised when dispatch cannot proceed safely."""


@dataclass(frozen=True)
class DispatchResult:
    success: bool
    output: str
    enforcement: EnforcementMode
    method: str  # "rc" or "subprocess"
    session_id: Optional[str] = None
    pid: Optional[int] = None
    status: Optional[DispatchStatus] = None
    output_path: Optional[Path] = None


@dataclass
class DispatchConfig:
    """Configuration for a dispatch operation."""

    repo_path: Path
    prompt: str
    mode: DispatchMode = DispatchMode.SUBPROCESS
    enforcement: Optional[EnforcementMode] = None
    timeout: Optional[int] = None
    on_complete: Optional[Callable[[DispatchResult], Any]] = None
