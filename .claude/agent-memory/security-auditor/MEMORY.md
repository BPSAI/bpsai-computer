# Security Auditor Memory

> This file is automatically loaded into the Security Auditor agent's system prompt (first 200 lines).
> Record audit findings, vulnerability patterns, and compliance observations specific to this project.

## Audit History
- [CD2 Sprint Audit (2026-03-30)](audit_cd2_sprint.md) — OutputStreamer/SessionLifecycle/Resume. 1 Critical, 3 High, 3 Medium, 3 Low.

## Vulnerability Patterns Found
- Raw stdout lines held unscrubbed in OutputStreamer.stdout_lines (feeds session ID extraction)
- Operator field bypass: missing field treated as match (falsy check, not explicit None check)
- Path traversal via target field (workspace_root / msg.target with no guard)
- session_id passed to subprocess args without format validation

## Compliance Checkpoints
- Credential scrubbing: partial — patterns miss GCP/GitHub/hex secrets
- Audit logging: lifecycle events posted to A2A backend (present)
- Encryption in transit: HTTPS to a2a.paircoder.ai (assumed, not pinned)

## Scan Targets
- `src/computer/scrubber.py` — credential pattern coverage
- `src/computer/streamer.py` — raw vs scrubbed line storage
- `src/computer/dispatcher.py` — subprocess arg construction, path traversal
- `src/computer/daemon.py` — operator scoping, poll loop input validation
- `src/computer/a2a_client.py` — HTTP client configuration, secrets in payloads
