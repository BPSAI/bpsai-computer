"""Repo classification and enforcement selection."""

from __future__ import annotations

from pathlib import Path

from computer.orchestration.config import (
    DispatchError,
    EnforcementMode,
    RepoType,
)


class RepoClassifier:
    """Detect repo type and select appropriate enforcement."""

    def classify(self, repo_path: Path) -> RepoType:
        """Detect whether a repo uses PairCoder or is a standard repo."""
        repo_path = Path(repo_path)
        if not repo_path.exists():
            raise DispatchError(f"Repo path does not exist: {repo_path}")
        if not repo_path.is_dir():
            raise DispatchError(f"Repo path is not a directory: {repo_path}")
        paircoder_dir = repo_path / ".paircoder"
        if paircoder_dir.is_dir() and (paircoder_dir / "config.yaml").exists():
            return RepoType.PAIRCODER
        return RepoType.STANDARD

    def enforcement_for(self, repo_type: RepoType) -> EnforcementMode:
        """Select enforcement mode based on repo type."""
        if repo_type == RepoType.PAIRCODER:
            return EnforcementMode.CONTAINED_AUTO
        return EnforcementMode.ALLOWED_TOOLS


# Module-level convenience functions (backward compat)
_default_classifier = RepoClassifier()


def detect_repo_type(repo_path: Path) -> RepoType:
    """Detect whether a repo uses PairCoder or is a standard repo."""
    return _default_classifier.classify(repo_path)


def select_enforcement(repo_type: RepoType) -> EnforcementMode:
    """Select enforcement mode based on repo type."""
    return _default_classifier.enforcement_for(repo_type)
