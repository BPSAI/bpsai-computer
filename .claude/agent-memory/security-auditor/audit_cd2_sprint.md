---
name: CD2 Sprint Audit — OutputStreamer, SessionLifecycle, Resume Handler
description: Security audit of bpsai-computer CD2 sprint (CD2.1–CD2.3): streaming, lifecycle, resume. Findings as of 2026-03-30.
type: project
---

Audit performed 2026-03-30 covering src/computer/scrubber.py, streamer.py, lifecycle.py, dispatcher.py, daemon.py, a2a_client.py, config.py.

**Why:** CD2 sprint added subprocess output streaming to A2A, session lifecycle events, and a --resume handler that uses --dangerously-skip-permissions.

**How to apply:** Reference these findings when reviewing follow-on sprints that touch the streaming path, operator scoping logic, or subprocess invocation.

## Key findings

### Critical
- SEV-001: `stdout_lines` property on OutputStreamer stores raw (unscrubbed) lines in memory. These feed `extract_session_id` in daemon.py. Any credential that appears in stdout will be held in-process until GC. No test verifies scrubbing of the raw buffer.

### High
- SEV-002: `session_id` in `parse_resume` is not validated against an allowlist or regex before being passed to `asyncio.create_subprocess_exec` as `["claude", "--resume", session_id, ...]`. Although `create_subprocess_exec` avoids shell interpretation, multi-token injection (spaces in session_id creating extra args) is untested and unblocked.
- SEV-003: Operator check in `_process_resume` is bypassable when the message has no `operator` field — the check only fires when `msg_operator` is truthy. A message without an operator field passes straight through to execution.
- SEV-004: `target` field in ResumeMessage is used as a path component (`workspace_root / msg.target`) with no path traversal guard. A target of `../../../etc` would resolve outside the workspace root if the directory existed.

### Medium
- SEV-005: `command` string logged to A2A lifecycle (session-started) contains the literal `session_id` value from the resume message. If session IDs ever embed sensitive context, this leaks into the A2A backend. No scrubbing applied before constructing the command string.
- SEV-006: scrubber patterns do not cover GCP service account tokens (ya29.*), GitHub PATs (ghp_*, github_pat_*), or generic hex secrets (32–64 char hex strings). Output from Claude subprocesses could contain these.
- SEV-007: `post_lifecycle` sends `output_summary` (last 10 lines of process output) to A2A after scrubbing only via the `_build_result` join. There is a window between `_read_stream` collecting lines into `stdout_lines` (unscrubbed) and `_build_result` scrubbing the joined text — raw lines are held in-process and passed to `extract_session_id`.

### Low
- SEV-008: A2AClient uses a new `httpx.AsyncClient()` per request with no connection pooling, timeout configuration, or TLS certificate pinning. Default httpx timeouts are generous.
- SEV-009: `_processed_ids` set in Daemon grows unbounded for the lifetime of the process. Very long-running daemons processing many messages will accumulate memory without eviction.
- SEV-010: `--dangerously-skip-permissions` is used for both normal dispatch and resume. This is documented as intentional for an orchestrator, but there is no runtime guard preventing use against repos outside workspace_root (path traversal via target field covers this too).
