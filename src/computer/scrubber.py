"""Credential scrubbing for subprocess output before posting to A2A."""

from __future__ import annotations

import re

# Patterns that match common credential formats
_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Anthropic API keys
    (re.compile(r"sk-ant-[a-zA-Z0-9\-_]{10,}"), "***REDACTED_API_KEY***"),
    # GitHub PATs (ghp_, github_pat_)
    (re.compile(r"ghp_[a-zA-Z0-9]{10,}"), "***REDACTED_GITHUB_PAT***"),
    (re.compile(r"github_pat_[a-zA-Z0-9_]{10,}"), "***REDACTED_GITHUB_PAT***"),
    # GCP OAuth tokens (ya29.)
    (re.compile(r"ya29\.[a-zA-Z0-9\-_]{10,}"), "***REDACTED_GCP_TOKEN***"),
    # OpenAI keys (sk-proj-, sk- but not sk-ant which is caught above)
    (re.compile(r"sk-(?!ant)[a-zA-Z0-9\-_]{10,}"), "***REDACTED_OPENAI_KEY***"),
    # AWS access keys
    (re.compile(r"AKIA[A-Z0-9]{16}"), "***REDACTED_AWS_KEY***"),
    # Bearer tokens (JWT-like)
    (re.compile(r"Bearer\s+[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+"), "Bearer ***REDACTED_TOKEN***"),
    # URL-embedded credentials (://user:pass@)
    (re.compile(r"(://)[^/@\s]+:[^/@\s]+(@)"), r"\1***REDACTED***\2"),
    # Generic secret assignments: password = "...", api_key = "..."
    (re.compile(r'((?:password|secret|token|api_key|apikey)\s*[=:]\s*["\'])([^"\']+)(["\'])', re.IGNORECASE), r"\1***REDACTED***\3"),
    # Environment variable exports with sk- or key-like values
    (re.compile(r"(export\s+\w*(?:KEY|SECRET|TOKEN|PASSWORD)\w*=)(\S+)", re.IGNORECASE), r"\1***REDACTED***"),
]


def scrub_credentials(text: str) -> str:
    """Remove credentials and secrets from text."""
    if not text:
        return text
    result = text
    for pattern, replacement in _PATTERNS:
        result = pattern.sub(replacement, result)
    return result
