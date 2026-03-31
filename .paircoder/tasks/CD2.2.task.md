---
id: CD2.2
title: Session lifecycle messages
plan: plan-2026-03-cd2
type: feature
priority: P0
complexity: 10
status: pending
sprint: "CD2"
tags: [lifecycle]
depends_on: []
trello_card_id: "29"
---

# Objective

Post structured lifecycle events when sessions start and complete. Extract Claude Code session ID from subprocess output. These events populate the Command Center session catalog (CC-S4 T2.3).

# Implementation Plan

- Post `session-started` on subprocess launch with session_id, operator, machine, workspace, command
- Extract Claude Code session ID from stdout (parse `Session: {id}` line, else generated UUID)
- Post `session-complete` on exit with exit_code, duration_seconds, output_summary
- Post `session-failed` on crash/timeout with error details
- All lifecycle messages routed via operator/workspace

# Acceptance Criteria

- [ ] Post `session-started` message on subprocess launch: session_id (from claude output or generated UUID), operator, machine, workspace, command, timestamp
- [ ] Extract Claude Code session ID from subprocess stdout (parse `Session: {id}` line if present, else use generated ID)
- [ ] Post `session-complete` message on subprocess exit: session_id, exit_code, duration_seconds, output_summary (last 10 lines), timestamp
- [ ] Post `session-failed` if subprocess crashes or times out: session_id, error, exit_code, timestamp
- [ ] Lifecycle messages posted to A2A dispatch channel with operator/workspace routing
- [ ] Tests: lifecycle message posting on start/complete/fail, session ID extraction, timeout handling

# Verification

- Dispatch task → `session-started` message in A2A with session_id
- Task completes → `session-complete` with duration and exit code
- Kill subprocess mid-run → `session-failed` with error
