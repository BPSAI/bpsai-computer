"""Dispatch orchestration, Navigator, and agent routing.

Extracted from bpsai-framework engine/dispatch/ and engine/navigator_orchestrator.py
during Phase C.

Modules:
    orchestrator  -- DispatchOrchestrator, ReviewResult
    dispatcher    -- Dispatcher, scrub_environment, build_command
    config        -- DispatchResult, DispatchError, DispatchMode, RepoType, EnforcementMode
    health_gate   -- BatchHealthGate, HealthGateConfig, HealthGateResult
    classifier    -- RepoClassifier, detect_repo_type, select_enforcement
    navigator     -- NavigatorOrchestrator, OrchestrationPhase, OrchestrationOutcome
"""

__all__: list[str] = [
    # orchestrator
    "DispatchOrchestrator",
    # dispatcher
    "Dispatcher",
    "scrub_environment",
    "build_command",
    # config
    "DispatchResult",
    "DispatchError",
    "DispatchMode",
    "DispatchStatus",
    "CompletionStatus",
    "RepoType",
    "EnforcementMode",
    # health_gate
    "BatchHealthGate",
    "HealthGateConfig",
    "HealthGateResult",
    # classifier
    "RepoClassifier",
    "detect_repo_type",
    "select_enforcement",
    # navigator
    "NavigatorOrchestrator",
    "OrchestrationPhase",
    "OrchestrationOutcome",
]
