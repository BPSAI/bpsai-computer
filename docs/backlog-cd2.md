# Computer Daemon CD2 — Session Streaming + Resume

> **Budget:** ~30cx
> **Depends on:** CD1 complete (daemon operational, 37 tests), A2A deployed (a2a.paircoder.ai live)
> **Repo:** bpsai-computer
> **Sprint ID:** CD2

---

## Context

CD1 built the core dispatch loop: poll A2A for commands, launch Claude Code subprocess, post results back. But sessions are fire-and-forget — no incremental output, no session ID tracking, and no resume capability.

CD2 adds real-time visibility into running sessions. The daemon streams stdout to A2A as it runs, posts session lifecycle events (started/complete), and handles resume commands. This is what makes sessions visible in Command Center (CC-S4) and enables resume-from-failure.

### Cross-Repo Dependencies

- **bpsai-a2a:** CD2 posts session lifecycle messages and streaming output to A2A endpoints. CC-S4 task CC4.3 adds the session catalog table. CD2 can post to generic A2A message endpoints initially.
- **bpsai-command-center (CC-S4):** CC4.4 and CC4.5 consume session data that CD2 produces. CD2 ships first, CC-S4 consumes.

---

### CD2.1 — Stream Stdout Incrementally | Cx: 15 | P0

**Description:** Read Claude Code subprocess output line-by-line and post incremental `session-output` messages to A2A. Currently the daemon waits for process completion then posts the full result. This task adds real-time streaming so operators can watch sessions in progress.

**AC:**
- [ ] Read subprocess stdout/stderr line-by-line (async, non-blocking)
- [ ] Post `session-output` messages to A2A with: session_id, line_number, content, stream (stdout/stderr), timestamp
- [ ] Configurable batch interval — buffer lines and post every N seconds (default 2s) to avoid flooding
- [ ] Credential scrubber runs on each line before posting (reuse existing scrubber from CD1)
- [ ] Graceful handling of rapid output (backpressure: drop oldest if buffer exceeds limit)
- [ ] Final result message still posted on process completion (backwards compatible with CD1 behavior)
- [ ] Tests: line-by-line reading, batched posting, credential scrubbing on stream, buffer overflow handling

### CD2.2 — Session Lifecycle Messages | Cx: 10 | P0

**Description:** Post structured lifecycle events when sessions start and complete. Extract Claude Code session ID from subprocess output. These events are what Command Center uses to populate the session catalog.

**AC:**
- [ ] Post `session-started` message on subprocess launch: session_id (from claude output or generated UUID), operator, machine, workspace, command, timestamp
- [ ] Extract Claude Code session ID from subprocess stdout (parse `Session: {id}` line if present, else use generated ID)
- [ ] Post `session-complete` message on subprocess exit: session_id, exit_code, duration_seconds, output_summary (last 10 lines), timestamp
- [ ] Post `session-failed` if subprocess crashes or times out: session_id, error, exit_code, timestamp
- [ ] Lifecycle messages posted to A2A dispatch channel with operator/workspace routing
- [ ] Tests: lifecycle message posting on start/complete/fail, session ID extraction, timeout handling

### CD2.3 — Resume Command Handler | Cx: 5 | P1

**Description:** Handle `type=resume` messages from the A2A dispatch channel. When received, run `claude --resume {session_id}` instead of a fresh `claude -p` session. This enables operators to resume failed or interrupted sessions from Command Center.

**Depends on:** CD2.2

**AC:**
- [ ] Recognize `type=resume` messages in the poll loop (alongside existing `type=dispatch`)
- [ ] Extract `session_id` from resume message payload
- [ ] Launch `claude --resume {session_id}` subprocess with same enforcement as regular dispatch
- [ ] Operator scoping enforced — resume message must match daemon's configured operator
- [ ] Post lifecycle messages (session-started with `resumed=true`, session-complete) same as fresh sessions
- [ ] Error handling: invalid session_id, session not resumable, Claude Code rejects resume
- [ ] Tests: resume command parsing, subprocess launch with --resume flag, operator scoping, error cases

---

## Summary

| Task | Title | Cx | Priority | Phase |
|------|-------|----|----------|-------|
| CD2.1 | Stream Stdout Incrementally | 15 | P0 | 1 |
| CD2.2 | Session Lifecycle Messages | 10 | P0 | 1 |
| CD2.3 | Resume Command Handler | 5 | P1 | 1 |
| **Total** | | **30** | | |

### Execution Order

```
Phase 1 (sequential):
  CD2.1 (streaming) + CD2.2 (lifecycle) can develop in parallel
  CD2.3 (resume) depends on CD2.2 for lifecycle message format
```

---

## Validation

After this sprint:
1. Dispatch a task via A2A → see incremental output lines appearing in A2A messages
2. Check A2A for `session-started` message with session_id, operator, machine
3. Wait for completion → `session-complete` message with duration and exit code
4. Send `type=resume` message → daemon picks it up and runs `claude --resume`
5. All output lines scrubbed of credentials before posting
