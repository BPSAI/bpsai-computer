"""Dispatch engine for launching Claude Code sessions in target repos.

Replaces scripts/dispatch_navigator.sh with a Python abstraction that
enforces security constraints per D-024: repo-type-aware enforcement,
credential scrubbing, RC/subprocess dispatch modes.

Key invariant: dispatch NEVER runs without enforcement.
"""

from computer.orchestration.classifier import (
    RepoClassifier,
    detect_repo_type,
    select_enforcement,
)
from computer.orchestration.config import (
    CREDENTIAL_KEYS,
    CREDENTIAL_PATTERNS,
    DEFAULT_ALLOWED_TOOLS,
    CompletionStatus,
    DispatchConfig,
    DispatchError,
    DispatchMode,
    DispatchResult,
    DispatchStatus,
    EnforcementMode,
    RepoType,
)
from computer.orchestration.orchestrator import (
    DispatchOrchestrator,
    ReviewResult,
)
from computer.orchestration.dispatcher import (
    Dispatcher,
    build_command,
    scrub_environment,
)

__all__ = [
    # Config & types
    "CompletionStatus",
    "CREDENTIAL_KEYS",
    "CREDENTIAL_PATTERNS",
    "DEFAULT_ALLOWED_TOOLS",
    "DispatchConfig",
    "DispatchError",
    "DispatchMode",
    "DispatchResult",
    "DispatchStatus",
    "EnforcementMode",
    "RepoType",
    # Classifier
    "RepoClassifier",
    "detect_repo_type",
    "select_enforcement",
    # Dispatcher
    "Dispatcher",
    "build_command",
    "scrub_environment",
    # Orchestrator
    "DispatchOrchestrator",
    "ReviewResult",
]
